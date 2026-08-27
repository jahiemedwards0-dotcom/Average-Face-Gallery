from __future__ import annotations

import base64
import gzip
import io
import json
import math
import re
import shutil
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
CACHE = ROOT / "pose_sort_cache"
PARTS = [ROOT / "pose_sort" / f"query3.part{i}" for i in range(4)]
MAX_OUTPUT_DIM = 1800
MAX_PROCESS_DIM = 1400
DOWNLOAD_WORKERS = 8
_tls = threading.local()


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
    return df.drop_duplicates(subset=["image"], keep="first").reset_index(drop=True)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "ChatGPT-PoseSorter/1.1 (Wikimedia Commons research batch)",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    })
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4))
    s.mount("http://", HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4))
    return s


def thread_session() -> requests.Session:
    if not hasattr(_tls, "session"):
        _tls.session = make_session()
    return _tls.session


def download_one(idx: int, source_url: str) -> dict:
    cache_path = CACHE / f"{idx:04d}.jpg"
    session = thread_session()
    last_error = None
    for u in (with_width(source_url, MAX_OUTPUT_DIM), source_url):
        try:
            r = session.get(u, timeout=(12, 45), allow_redirects=True)
            r.raise_for_status()
            if not r.content:
                raise ValueError("empty response")
            im = Image.open(io.BytesIO(r.content))
            im.seek(0)
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((MAX_OUTPUT_DIM, MAX_OUTPUT_DIM), Image.Resampling.LANCZOS)
            im.save(cache_path, "JPEG", quality=92, optimize=True)
            return {"idx": idx, "cache_path": str(cache_path), "downloaded_url": r.url, "error": ""}
        except Exception as exc:
            last_error = exc
    return {"idx": idx, "cache_path": "", "downloaded_url": "", "error": f"{type(last_error).__name__}: {last_error}"[:300]}


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
    return best


def estimate_pose(face_landmarks, width: int, height: int) -> tuple[float | None, float | None]:
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
        ok, rvec, _ = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
        if ok:
            rot, _ = cv2.Rodrigues(rvec)
            yaw = float(cv2.RQDecomp3x3(rot)[0][1])
            if yaw > 180:
                yaw -= 360
            if yaw < -180:
                yaw += 360
    except Exception:
        yaw = None

    nose_x = float(face_landmarks.landmark[1].x)
    left_edge_x = float(face_landmarks.landmark[234].x)
    right_edge_x = float(face_landmarks.landmark[454].x)
    dl, dr = abs(nose_x - left_edge_x), abs(right_edge_x - nose_x)
    symmetry = float(min(dl, dr) / max(dl, dr)) if max(dl, dr) > 1e-6 else None
    return yaw, symmetry


def classify_pose(yaw: float | None, symmetry: float | None) -> str:
    ay = abs(yaw) if yaw is not None and math.isfinite(yaw) else None
    sy = symmetry if symmetry is not None and math.isfinite(symmetry) else None
    if (ay is not None and ay >= 60.0) or (sy is not None and sy <= 0.22):
        return "side"
    if (ay is not None and ay <= 16.0) and (sy is None or sy >= 0.68):
        return "front"
    return "three_quarter"


def main() -> None:
    for p in (WORK, CACHE):
        if p.exists():
            shutil.rmtree(p)
    for folder in ("front", "three_quarter", "side", "unclassified"):
        (WORK / folder).mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    df = load_dataframe()
    total = len(df)
    print(f"Unique images: {total}; parallel download workers: {DOWNLOAD_WORKERS}", flush=True)

    downloads = {}
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        futures = {pool.submit(download_one, i, str(row["image"])): i for i, row in df.iterrows()}
        done = 0
        for fut in as_completed(futures):
            res = fut.result()
            downloads[res["idx"]] = res
            done += 1
            if done % 20 == 0 or done == total:
                ok = sum(1 for x in downloads.values() if not x["error"])
                print(f"Downloaded {done}/{total} ({ok} usable so far)", flush=True)

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=5,
        refine_landmarks=False,
        min_detection_confidence=0.40,
    )

    manifest = []
    for idx, row in df.iterrows():
        person = str(row.get("personLabel", "person"))
        stem = f"{idx+1:04d}_{slugify(person)}"
        filename = f"{stem}.jpg"
        category = "unclassified"
        yaw = symmetry = None
        face_count = 0
        dl = downloads.get(idx, {"cache_path": "", "downloaded_url": "", "error": "missing download result"})
        status = "ok"

        if dl["error"]:
            status = f"download_error: {dl['error']}"
            filename = ""
        else:
            try:
                im = Image.open(dl["cache_path"]).convert("RGB")
                proc = im.copy()
                proc.thumbnail((MAX_PROCESS_DIM, MAX_PROCESS_DIM), Image.Resampling.LANCZOS)
                result = face_mesh.process(np.asarray(proc))
                faces = result.multi_face_landmarks or []
                face_count = len(faces)
                if not faces:
                    status = "no_face_detected"
                else:
                    face = largest_face(faces)
                    yaw, symmetry = estimate_pose(face, proc.width, proc.height)
                    category = classify_pose(yaw, symmetry)
                    if face_count > 1:
                        status = "multiple_faces_largest_used"
                shutil.copy2(dl["cache_path"], WORK / category / filename)
            except Exception as exc:
                status = f"processing_error: {type(exc).__name__}: {exc}"[:300]
                filename = ""

        record = {k: row.get(k, "") for k in df.columns}
        record.update({
            "category": category,
            "yaw_deg": yaw,
            "symmetry": symmetry,
            "face_count": face_count,
            "status": status,
            "saved_filename": filename,
            "downloaded_url": dl.get("downloaded_url", ""),
        })
        manifest.append(record)
        if (idx + 1) % 25 == 0 or idx + 1 == total:
            print(f"Classified {idx+1}/{total}", flush=True)

    face_mesh.close()
    manifest_df = pd.DataFrame(manifest)
    manifest_df.to_csv(WORK / "manifest.csv", index=False)
    counts = manifest_df["category"].value_counts(dropna=False).to_dict()
    statuses = manifest_df["status"].value_counts(dropna=False).to_dict()
    summary = {
        "input_rows_after_unique_image_deduplication": int(total),
        "counts": {str(k): int(v) for k, v in counts.items()},
        "status_counts": {str(k): int(v) for k, v in statuses.items()},
        "classification_rule": {
            "front": "abs(yaw) <= 16 deg and symmetry >= 0.68",
            "side": "abs(yaw) >= 60 deg or symmetry <= 0.22",
            "three_quarter": "everything between front and side",
            "unclassified": "no usable face or download/decode failure",
        },
    }
    (WORK / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    shutil.rmtree(CACHE, ignore_errors=True)


if __name__ == "__main__":
    main()
