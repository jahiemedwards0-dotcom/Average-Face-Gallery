# Face-detection gate

Every candidate image must contain at least one detectable human face before it is kept.

## Filtering a downloaded batch

For a ZIP archive:

```bash
python -m pip install -r requirements-face-filter.txt
python tools/filter_faces.py public_figures.zip \
  --output public_figures_faces_only.zip \
  --manifest face_detection_manifest.csv
```

The output ZIP contains **only images that passed face detection**. Files with zero detected faces are omitted automatically.

For an unpacked directory:

```bash
python tools/filter_faces.py photos/ \
  --delete-rejected \
  --manifest face_detection_manifest.csv
```

`--delete-rejected` physically removes files with zero detected faces.

## Detection rules

Each image is checked independently. The filter uses:

1. OpenCV YuNet face detection at a 0.70 confidence threshold.
2. Frontal and profile Haar-cascade detection as a fallback.
3. 0°, 90°, 180°, and 270° orientations to avoid missing rotated images.
4. A minimum detectable face size of 32 px by default.

The manifest records the file, whether a face was detected, the detector used, confidence when available, face count, and whether the file was kept or rejected.

## GitHub enforcement

`.github/workflows/face-detection-gate.yml` runs the detector against every image in `images/` whenever image files or the detector itself change. A pull request fails if **any** image has zero detectable faces.

For external public-figure batches, always run `tools/filter_faces.py` before packaging or uploading the final archive. Do not substitute profile-page metadata or filenames for pixel-level face detection.
