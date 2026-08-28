#!/usr/bin/env python3
"""Fill slot 36 in the 49-face archive with Jazlyn Oviedo's exact UVM headshot.

The input archive is the 49/50 artifact from the identity-safe patch run. The exact
University of Vermont headshot URL is tied to Jazlyn Oviedo's official roster profile.
The image is accepted only if the repository's strict YuNet detector finds a face.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from filter_faces import (
    DEFAULT_MIN_FACE_PX,
    DEFAULT_SCORE_THRESHOLD,
    detect_face,
    ensure_yunet_model,
    read_image,
)

JAZLYN_NAME = "Jazlyn Oviedo"
JAZLYN_PROFILE = "https://uvmathletics.com/sports/womens-soccer/roster/jazlyn-oviedo/12301"
JAZLYN_IMAGE = "https://d2qo6i29smt6hw.cloudfront.net/images/2025/7/30/Oviedo_Jazlyn.jpg?width=300"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
USER_AGENT = "Mozilla/5.0 (compatible; FaceValidationBot/1.0; +https://github.com/)"


def download(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(25_000_001)
    if len(data) > 25_000_000:
        raise RuntimeError("headshot exceeded size limit")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-zip", type=Path, required=True)
    ap.add_argument("--input-manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--output-manifest", type=Path, required=True)
    args = ap.parse_args()

    rows = list(csv.DictReader(args.input_manifest.open(encoding="utf-8")))
    if len(rows) != 50:
        raise RuntimeError(f"expected 50 manifest rows, got {len(rows)}")
    row36 = next((r for r in rows if int(r["index"]) == 36), None)
    if row36 is None:
        raise RuntimeError("slot 36 missing from manifest")

    model = ensure_yunet_model()

    with tempfile.TemporaryDirectory(prefix="final_face_") as td:
        work = Path(td)
        image_dir = work / "images"
        image_dir.mkdir()

        with zipfile.ZipFile(args.input_zip) as zf:
            for info in zf.infolist():
                suffix = Path(info.filename).suffix.lower()
                if suffix not in IMAGE_EXTS:
                    continue
                name = Path(info.filename).name
                if name.startswith("36_"):
                    continue
                (image_dir / name).write_bytes(zf.read(info))

        existing = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if len(existing) != 49:
            raise RuntimeError(f"expected 49 retained images, got {len(existing)}")

        existing_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in existing}
        if len(existing_hashes) != 49:
            raise RuntimeError("duplicate image bytes already present in 49-face base")

        data = download(JAZLYN_IMAGE)
        digest = hashlib.sha256(data).hexdigest()
        if digest in existing_hashes:
            raise RuntimeError("Jazlyn headshot duplicates an existing image")

        candidate = work / "jazlyn.jpg"
        candidate.write_bytes(data)
        if read_image(candidate) is None:
            raise RuntimeError("Jazlyn headshot did not decode as an image")

        result = detect_face(
            candidate,
            DEFAULT_SCORE_THRESHOLD,
            DEFAULT_MIN_FACE_PX,
            model,
        )
        if not result["detected"]:
            raise RuntimeError(f"Jazlyn headshot failed strict face detection: {result['detector']}")

        dest = image_dir / "36_Jazlyn_Oviedo.jpg"
        shutil.copy2(candidate, dest)

        row36.update(
            {
                "name": JAZLYN_NAME,
                "status": "replacement",
                "source_page": JAZLYN_PROFILE,
                "image_url": JAZLYN_IMAGE,
                "detector": result["detector"],
                "score": str(result["score"]),
                "face_count": str(result["face_count"]),
                "sha256": digest,
            }
        )

        fields = [
            "index",
            "name",
            "status",
            "source_page",
            "image_url",
            "detector",
            "score",
            "face_count",
            "sha256",
        ]
        with args.output_manifest.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        final_images = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if len(final_images) != 50:
            raise RuntimeError(f"expected 50 final images, got {len(final_images)}")

        with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in final_images:
                zf.write(p, p.name)
            zf.write(args.output_manifest, args.output_manifest.name)

    print(
        f"slot 36 PASS {result['detector']} score={result['score']}; "
        f"candidate ZIP now contains 50 images"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
