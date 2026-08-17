#!/usr/bin/env python3
"""Filter image batches so only files with at least one detectable human face remain.

Usage examples:
  python tools/filter_faces.py input.zip --output faces_only.zip
  python tools/filter_faces.py photos/ --delete-rejected --manifest face_detection_manifest.csv
  python tools/filter_faces.py images/ --fail-on-rejected

Detection strategy:
  1. OpenCV YuNet face detector (primary)
  2. OpenCV frontal/profile Haar cascades (fallback)
  3. Test 0/90/180/270-degree rotations so EXIF/orientation mistakes do not hide faces

For ZIP input, rejected images are never copied to the output ZIP. For directory input,
pass --delete-rejected to physically remove rejected files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile

import cv2
import numpy as np


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
MODEL_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
    "face_detection_yunet_2023mar.onnx"
)
MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
DEFAULT_SCORE_THRESHOLD = 0.70
DEFAULT_MIN_FACE_PX = 32
MAX_DETECTION_EDGE = 1600


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_yunet_model() -> Path | None:
    """Download the pinned YuNet model once; return None if unavailable."""
    cache_dir = Path(os.environ.get("FACE_FILTER_CACHE", Path.home() / ".cache" / "face-filter"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / "face_detection_yunet_2023mar.onnx"

    if model_path.exists() and _sha256(model_path) == MODEL_SHA256:
        return model_path

    try:
        tmp = model_path.with_suffix(".tmp")
        urllib.request.urlretrieve(MODEL_URL, tmp)
        if _sha256(tmp) != MODEL_SHA256:
            tmp.unlink(missing_ok=True)
            raise RuntimeError("YuNet model checksum mismatch")
        tmp.replace(model_path)
        return model_path
    except Exception as exc:  # network/model failure should not stop Haar fallback
        print(f"warning: YuNet unavailable ({exc}); using Haar fallback", file=sys.stderr)
        return None


def read_image(path: Path) -> np.ndarray | None:
    """Read an image robustly, including Unicode filenames."""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def resize_for_detection(image: np.ndarray) -> tuple[np.ndarray, float]:
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= MAX_DETECTION_EDGE:
        return image, 1.0
    scale = MAX_DETECTION_EDGE / float(longest)
    resized = cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale


def rotations(image: np.ndarray):
    yield 0, image
    yield 90, cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    yield 180, cv2.rotate(image, cv2.ROTATE_180)
    yield 270, cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def detect_yunet(image: np.ndarray, model_path: Path, threshold: float, min_face_px: int):
    h, w = image.shape[:2]
    detector = cv2.FaceDetectorYN_create(
        str(model_path), "", (w, h), threshold, 0.3, 5000
    )
    _, faces = detector.detect(image)
    if faces is None:
        return []

    detected = []
    for face in faces:
        x, y, fw, fh = face[:4]
        score = float(face[-1])
        if fw >= min_face_px and fh >= min_face_px and score >= threshold:
            detected.append((score, (float(x), float(y), float(fw), float(fh))))
    return detected


def detect_haar(image: np.ndarray, min_face_px: int):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    base = Path(cv2.data.haarcascades)
    frontal = cv2.CascadeClassifier(str(base / "haarcascade_frontalface_default.xml"))
    profile = cv2.CascadeClassifier(str(base / "haarcascade_profileface.xml"))

    params = dict(scaleFactor=1.08, minNeighbors=5, minSize=(min_face_px, min_face_px))
    boxes = list(frontal.detectMultiScale(gray, **params))
    boxes += list(profile.detectMultiScale(gray, **params))
    # Profile cascade is directional; flipping catches the opposite profile.
    boxes += list(profile.detectMultiScale(cv2.flip(gray, 1), **params))
    return boxes


def detect_face(path: Path, threshold: float, min_face_px: int, model_path: Path | None):
    image = read_image(path)
    if image is None or image.size == 0:
        return {"detected": False, "detector": "unreadable", "score": "", "face_count": 0}

    image, scale = resize_for_detection(image)
    scaled_min = max(20, round(min_face_px * scale))

    for angle, candidate in rotations(image):
        if model_path is not None:
            faces = detect_yunet(candidate, model_path, threshold, scaled_min)
            if faces:
                best = max(score for score, _ in faces)
                return {
                    "detected": True,
                    "detector": f"yunet@{angle}",
                    "score": f"{best:.4f}",
                    "face_count": len(faces),
                }

        boxes = detect_haar(candidate, scaled_min)
        if boxes:
            return {
                "detected": True,
                "detector": f"haar@{angle}",
                "score": "",
                "face_count": len(boxes),
            }

    return {"detected": False, "detector": "none", "score": "", "face_count": 0}


def iter_images(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            yield path


def write_manifest(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "detected", "detector", "score", "face_count", "action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def process_directory(
    root: Path,
    *,
    threshold: float,
    min_face_px: int,
    model_path: Path | None,
    delete_rejected: bool,
):
    rows = []
    rejected = []
    images = list(iter_images(root))

    for idx, path in enumerate(images, 1):
        result = detect_face(path, threshold, min_face_px, model_path)
        rel = path.relative_to(root).as_posix()
        if result["detected"]:
            action = "kept"
        else:
            rejected.append(path)
            action = "deleted" if delete_rejected else "rejected"
            if delete_rejected:
                path.unlink(missing_ok=True)

        rows.append({"file": rel, **result, "action": action})
        print(f"[{idx}/{len(images)}] {'PASS' if result['detected'] else 'DROP'} {rel} ({result['detector']})")

    return rows, rejected


def safe_extract_zip(src: Path, dst: Path):
    with zipfile.ZipFile(src) as zf:
        for member in zf.infolist():
            target = (dst / member.filename).resolve()
            if not str(target).startswith(str(dst.resolve())):
                raise RuntimeError(f"unsafe ZIP path: {member.filename}")
        zf.extractall(dst)


def build_filtered_zip(extracted_root: Path, output_zip: Path, rows: list[dict], manifest_path: Path):
    rejected = {row["file"] for row in rows if not row["detected"]}
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(extracted_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(extracted_root).as_posix()
            if path.suffix.lower() in SUPPORTED_EXTS and rel in rejected:
                continue
            zf.write(path, rel)
        zf.write(manifest_path, "face_detection_manifest.csv")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject images that contain no detectable human face")
    parser.add_argument("input", type=Path, help="Image directory or ZIP archive")
    parser.add_argument("--output", type=Path, help="Output ZIP when input is a ZIP")
    parser.add_argument("--manifest", type=Path, default=Path("face_detection_manifest.csv"))
    parser.add_argument("--delete-rejected", action="store_true", help="Delete failed images for directory input")
    parser.add_argument("--fail-on-rejected", action="store_true", help="Exit non-zero if any image fails")
    parser.add_argument("--score-threshold", type=float, default=DEFAULT_SCORE_THRESHOLD)
    parser.add_argument("--min-face-px", type=int, default=DEFAULT_MIN_FACE_PX)
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"input not found: {args.input}")

    model_path = ensure_yunet_model()

    if args.input.is_dir():
        rows, rejected = process_directory(
            args.input,
            threshold=args.score_threshold,
            min_face_px=args.min_face_px,
            model_path=model_path,
            delete_rejected=args.delete_rejected,
        )
        write_manifest(args.manifest, rows)
    elif zipfile.is_zipfile(args.input):
        output = args.output or args.input.with_name(f"{args.input.stem}_faces_only.zip")
        with tempfile.TemporaryDirectory(prefix="face-filter-") as td:
            root = Path(td)
            safe_extract_zip(args.input, root)
            rows, rejected = process_directory(
                root,
                threshold=args.score_threshold,
                min_face_px=args.min_face_px,
                model_path=model_path,
                delete_rejected=True,
            )
            write_manifest(args.manifest, rows)
            build_filtered_zip(root, output, rows, args.manifest)
            print(f"filtered ZIP: {output}")
    else:
        parser.error("input must be a directory or ZIP archive")

    passed = sum(bool(row["detected"]) for row in rows)
    failed = len(rows) - passed
    print(f"checked={len(rows)} passed={passed} rejected={failed} manifest={args.manifest}")

    if not rows:
        print("error: no supported image files found", file=sys.stderr)
        return 2
    if args.fail_on_rejected and rejected:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
