#!/usr/bin/env python3
"""Filter image batches so only files with a YuNet-detectable human face remain.

Usage examples:
  python tools/filter_faces.py input.zip --output faces_only.zip
  python tools/filter_faces.py photos/ --delete-rejected --manifest face_detection_manifest.csv
  python tools/filter_faces.py images/ --exclude-glob '*map*' --fail-on-rejected

Hard rule:
  * Every candidate image is decoded and checked independently.
  * A file is kept only when OpenCV YuNet detects >=1 face above threshold.
  * The detector is tried at 0/90/180/270 degrees.
  * If YuNet cannot be loaded, the run FAILS CLOSED. No weaker detector may approve files.

For ZIP input, rejected images are never copied to the output ZIP. For directory input,
pass --delete-rejected to physically remove rejected files.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import urllib.request
import zipfile

import cv2
import numpy as np


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
# GitHub's normal raw URL returns an LFS pointer for this model. The media endpoint
# returns the actual pinned LFS object bytes.
MODEL_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
DEFAULT_SCORE_THRESHOLD = 0.75
DEFAULT_MIN_FACE_PX = 32
MAX_DETECTION_EDGE = 1600


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_yunet_model() -> Path:
    """Download the pinned YuNet model once. Fail closed if it cannot be verified."""
    cache_dir = Path(os.environ.get("FACE_FILTER_CACHE", Path.home() / ".cache" / "face-filter"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / "face_detection_yunet_2023mar.onnx"

    if model_path.exists() and _sha256(model_path) == MODEL_SHA256:
        return model_path

    tmp = model_path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    try:
        urllib.request.urlretrieve(MODEL_URL, tmp)
        digest = _sha256(tmp)
        if digest != MODEL_SHA256:
            raise RuntimeError(
                f"YuNet model checksum mismatch: expected {MODEL_SHA256}, got {digest}"
            )
        tmp.replace(model_path)
        return model_path
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "YuNet face detector could not be loaded and verified; refusing to approve any images"
        ) from exc


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


def detect_face(path: Path, threshold: float, min_face_px: int, model_path: Path):
    image = read_image(path)
    if image is None or image.size == 0:
        return {"detected": False, "detector": "unreadable", "score": "", "face_count": 0}

    image, scale = resize_for_detection(image)
    scaled_min = max(20, round(min_face_px * scale))

    best_faces = []
    best_angle = 0
    for angle, candidate in rotations(image):
        faces = detect_yunet(candidate, model_path, threshold, scaled_min)
        if len(faces) > len(best_faces):
            best_faces = faces
            best_angle = angle
        elif faces and best_faces:
            if max(score for score, _ in faces) > max(score for score, _ in best_faces):
                best_faces = faces
                best_angle = angle

    if best_faces:
        best_score = max(score for score, _ in best_faces)
        return {
            "detected": True,
            "detector": f"yunet@{best_angle}",
            "score": f"{best_score:.4f}",
            "face_count": len(best_faces),
        }

    return {"detected": False, "detector": "yunet-none", "score": "", "face_count": 0}


def excluded(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(Path(rel_path).name, pattern) for pattern in patterns)


def iter_images(root: Path, exclude_globs: list[str]):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        rel = path.relative_to(root).as_posix()
        if excluded(rel, exclude_globs):
            continue
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
    model_path: Path,
    delete_rejected: bool,
    exclude_globs: list[str],
):
    rows = []
    rejected = []
    images = list(iter_images(root, exclude_globs))

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
        print(
            f"[{idx}/{len(images)}] {'PASS' if result['detected'] else 'DROP'} "
            f"{rel} ({result['detector']}{' score=' + result['score'] if result['score'] else ''})"
        )

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
    parser = argparse.ArgumentParser(description="Reject images that contain no YuNet-detectable human face")
    parser.add_argument("input", type=Path, help="Image directory or ZIP archive")
    parser.add_argument("--output", type=Path, help="Output ZIP when input is a ZIP")
    parser.add_argument("--manifest", type=Path, default=Path("face_detection_manifest.csv"))
    parser.add_argument("--delete-rejected", action="store_true", help="Delete failed images for directory input")
    parser.add_argument("--fail-on-rejected", action="store_true", help="Exit non-zero if any candidate image fails")
    parser.add_argument("--score-threshold", type=float, default=DEFAULT_SCORE_THRESHOLD)
    parser.add_argument("--min-face-px", type=int, default=DEFAULT_MIN_FACE_PX)
    parser.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        help="Exclude intentional non-face assets (repeatable). ZIP/public-figure batches should normally omit this option.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"input not found: {args.input}")

    try:
        model_path = ensure_yunet_model()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    if args.input.is_dir():
        rows, rejected = process_directory(
            args.input,
            threshold=args.score_threshold,
            min_face_px=args.min_face_px,
            model_path=model_path,
            delete_rejected=args.delete_rejected,
            exclude_globs=args.exclude_glob,
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
                exclude_globs=args.exclude_glob,
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
        print("error: no supported candidate image files found", file=sys.stderr)
        return 2
    if args.fail_on_rejected and rejected:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
