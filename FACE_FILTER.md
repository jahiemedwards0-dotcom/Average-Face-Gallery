# Face-detection gate

Every candidate image must contain at least one YuNet-detectable human face before it is kept.

## Filtering a downloaded batch

For a ZIP archive:

```bash
python -m pip install -r requirements-face-filter.txt
python tools/filter_faces.py public_figures.zip \
  --output public_figures_faces_only.zip \
  --manifest face_detection_manifest.csv
```

The output ZIP contains **only images that passed face detection**. Files with zero detected faces are omitted automatically. Public-figure ZIP batches should not use exclusions.

For an unpacked directory:

```bash
python tools/filter_faces.py photos/ \
  --delete-rejected \
  --manifest face_detection_manifest.csv
```

`--delete-rejected` physically removes files with zero detected faces.

## Detection rules

Each candidate image is checked independently. The filter:

1. Uses the pinned OpenCV YuNet model as the **only detector allowed to approve an image**.
2. Requires a YuNet confidence score of at least **0.75** by default.
3. Checks 0°, 90°, 180°, and 270° orientations.
4. Requires a minimum face size of 32 px by default.
5. Verifies the model SHA-256 before use.
6. **Fails closed** if the YuNet model cannot be downloaded, verified, or loaded; it never falls back to a weaker detector to approve files.

The manifest records the file, whether a face was detected, detector/orientation, confidence, face count, and whether the file was kept or rejected/deleted.

## GitHub enforcement

`.github/workflows/face-detection-gate.yml` runs the same strict detector against the repository's intended face assets whenever image files or the detector itself change. Intentional `*map*` assets are excluded from repository CI because they are known non-face assets. This exception is **not** used for public-figure ZIP batches.

For external public-figure batches, always run `tools/filter_faces.py` before packaging or uploading the final archive. Do not substitute profile-page metadata, filenames, or a permissive Haar cascade for pixel-level YuNet detection.
