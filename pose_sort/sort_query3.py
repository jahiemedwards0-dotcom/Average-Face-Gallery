from __future__ import annotations

import base64
import gzip
import io
import json
import math
import re
import shutil
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageOps
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "pose_sort_output"
PARTS = [ROOT / "pose_sort" / f"query3.part{i}" for i in range(4)]
MAX_OUTPUT_DIM = 1800
MAX_PROCESS_DIM = 1400


def slugify(text: str, max_len: int = 90) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return (text[:max_len] or "person").strip("_")


def with_width(url: str, width: int = 1800) -> str:
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q["width"] = str(width)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def load_dataframe() -> pd.DataFrame:
    encoded = "".join(p.read_text(encoding="utf-8").strip() for p in PARTS)
    raw = gzip.decompress(base64.b64decode(encoded))
    df = pd.read_csv(io.BytesIO(raw))
    df = df.dropna(subset=["image"]).copy()
    df = df.drop_duplicates(subset=["image"], keep="first").reset_index(drop=True)
    return df


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "ChatGPT-PoseSorter/1.0 (Wikimedia Commons research batch; contact via GitHub repo)",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    })
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def download_image(session: requests.Session, source_url: str) -> tuple[Image.Image, str]:
    attempts = [with_width(source_url, MAX_OUTPUT_DIM), source_url]
    last_error = None
    for u in attempts:
        try:
            r = session.get(u, timeout=(15, 60), allow_redirects=True)
            r.raise_for_status()
            if not r.content:
                raise ValueError("empty response")
            im = Image.open(io.BytesIO(r.content))
            im.seek(0)
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            elif im.mode == "L":
                im = im.convert("RGB")
            return im, r.url
        except Exception as exc:
            last_error = exc
    raise RuntimeError(str(last_error) if last_error else "download failed")


def resize_for_processing(im: Image.Image) -> Image.Image:
    p = im.copy()
    p.thumbnail((MAX_PROCESS_DIM, MAX_PROCESS_DIM), Image.Resampling.LANCZOS)
    return p


def largest_face(face_landmarks_list):
    best = None
    best_area = -1.0
    for lm in face_landmarks_list:
        xs = np.array([p.x for p in lm.landmark], dtype=np.float64)
        ys = np.array([p.y for p in lm.landmark], dtype=np.float64)
        area = float((xs.max() - xs.min()) * (ys.max() - ys.min()))
        if area > best_area:
            best_area = area
            best = lm
    return best, best_area


def estimate_pose(face_landmarks, width: int, height: int) -> tuple[float | None, float | None]:
    # MediaPipe landmark indices: nose tip, chin, eye corners, mouth corners.
    ids = [1, 152, 33, 263, 61, 291]
    image_points = np.array(
        [[face_landmarks.landmark[i].x * width, face_landmarks.landmark[i].y * height] for i in ids],
        dtype=np.float64,
    )

    model_points = np.array(
        [
            (0.0, 0.0, 0.0),
            (0.0, -63.6, -12.5),
            (-43.3, 32.7, -26.0),
            (43.3, 32.7, -26.0),
            (-28.9, -28.9, -24.1),
            (28.9, -28.9, -24.1),
        ],
        dtype=np.float64,
    )

    focal = float(width)
    camera_matrix = np.array(
        [[focal, 0, width / 2.0], [0, focal, height / 2.0], [0, 0, 1]], dtype=np.float64
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    yaw = None
    try:
        ok, rvec, _ = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if ok:
            rot, _ = cv2.Rodrigues(rvec)
            angles = cv2.RQDecomp3x3(rot)[0]
            yaw = float(angles[1])
            if yaw > 180:
                yaw -= 360
            if yaw < -180:
                yaw += 360
    except Exception:
        yaw = None

    # A second cue based on left/right facial width asymmetry around the nose.
    nose_x = float(face_landmarks.landmark[1].x)
    left_edge_x = float(face_landmarks.landmark[234].x)
    right_edge_x = float(face_landmarks.landmark[454].x)
    dl = abs(nose_x - left_edge_x)
    dr = abs(right_edge_x - nose_x)
    symmetry = None
    if max(dl, dr) > 1e-6:
        symmetry = float(min(dl, dr) / max(dl, dr))

    return yaw, symmetry


def classify_pose(yaw: float | None, symmetry: float | None) -> str:
    ay = abs(yaw) if yaw is not None and math.isfinite(yaw) else None
    sy = symmetry if symmetry is not None and math.isfinite(symmetry) else None

    # Conservative bins: near-profile is side; visibly rotated is three-quarter;
    # only close-to-symmetric, low-yaw faces are called front.
    if (ay is not None and ay >= 60.0) or (sy is not None and sy <= 0.22):
        return "side"
    if (ay is not None and ay <= 16.0) and (sy is None or sy >= 0.68):
        return "front"
    return "three_quarter"


def main() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    for folder in ("front", "three_quarter", "side", "unclassified"):
        (WORK / folder).mkdir(parents=True, exist_ok=True)

    df = load_dataframe()
    session = make_session()
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=5,
        refine_landmarks=False,
        min_detection_confidence=0.40,
    )

    manifest = []
    total = len(df)

    for idx, row in df.iterrows():
        person = str(row.get("personLabel", "person"))
        source = str(row["image"])
        stem = f"{idx+1:04d}_{slugify(person)}"
        category = "unclassified"
        yaw = None
        symmetry = None
        face_count = 0
        downloaded_url = ""
        status = "ok"
        filename = f"{stem}.jpg"

        try:
            im, downloaded_url = download_image(session, source)
            out_im = im.copy()
            out_im.thumbnail((MAX_OUTPUT_DIM, MAX_OUTPUT_DIM), Image.Resampling.LANCZOS)

            proc = resize_for_processing(im)
            rgb = np.asarray(proc.convert("RGB"))
            result = face_mesh.process(rgb)
            faces = result.multi_face_landmarks or []
            face_count = len(faces)

            if not faces:
                status = "no_face_detected"
                category = "unclassified"
            else:
                face, _ = largest_face(faces)
                yaw, symmetry = estimate_pose(face, proc.width, proc.height)
                category = classify_pose(yaw, symmetry)
                if face_count > 1:
                    status = "multiple_faces_largest_used"

            out_path = WORK / category / filename
            out_im.convert("RGB").save(out_path, format="JPEG", quality=92, optimize=True)

        except Exception as exc:
            status = f"error: {type(exc).__name__}: {exc}"[:300]
            filename = ""
            print(f"[{idx+1}/{total}] ERROR {person}: {status}", flush=True)
        else:
            print(
                f"[{idx+1}/{total}] {category:14s} yaw={yaw!s:>8} sym={symmetry!s:>8} faces={face_count} {person}",
                flush=True,
            )

        record = {k: row.get(k, "") for k in df.columns}
        record.update(
            {
                "category": category,
                "yaw_deg": yaw,
                "symmetry": symmetry,
                "face_count": face_count,
                "status": status,
                "saved_filename": filename,
                "downloaded_url": downloaded_url,
            }
        )
        manifest.append(record)
        time.sleep(0.05)

    face_mesh.close()
    manifest_df = pd.DataFrame(manifest)
    manifest_df.to_csv(WORK / "manifest.csv", index=False)

    counts = manifest_df["category"].value_counts(dropna=False).to_dict()
    statuses = manifest_df["status"].value_counts(dropna=False).to_dict()
    summary = {
        "input_rows_after_unique_image_deduplication": int(len(df)),
        "counts": {str(k): int(v) for k, v in counts.items()},
        "status_counts": {str(k): int(v) for k, v in statuses.items()},
        "classification_rule": {
            "front": "abs(yaw) <= 16 deg and symmetry >= 0.68",
            "side": "abs(yaw) >= 60 deg or symmetry <= 0.22",
            "three_quarter": "everything between front and side",
            "unclassified": "no usable face / download or decode failure",
        },
    }
    (WORK / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
