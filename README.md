# Wikimedia Commons image harvest + YuNet face-view pipeline

This repository contains a resumable, serial Wikimedia Commons harvesting pipeline for the supplied `expanded_manifest.csv`.

**Candidate records are not downloaded images.** The source manifest contains exactly **4,212 candidate rows**. A record is counted as a successfully downloaded image only after the Commons thumbnail request succeeds, Pillow can decode the returned bytes, and a SHA-256 hash is recorded.

## Safety and data-use rules

- Gender is copied only from the supplied CSV. Blank values become `unknown` for folder organization.
- The pipeline does **not** infer gender, ethnicity, ancestry, nationality, or identity from appearance.
- Face processing is limited to detection, quality triage, and coarse head-view classification.
- Exact duplicate files are detected with SHA-256. Duplicate records stay in the manifests, but repeated bytes are not retained unnecessarily.

## Input

The exact uploaded input is bzip2-compressed and base64-split under `data/manifest/` so it can be committed reliably through the GitHub connector. The workflow concatenates the parts, reconstructs `expanded_manifest.csv.bz2`, expands it to `expanded_manifest.csv`, verifies the uncompressed SHA-256, and asserts exactly 4,212 unique `candidate_id` values.

Uncompressed input SHA-256: `39ae38585ffacd57e22589b747dd59459235590d64e305e38c701e5c5320a4e0`.

## Wikimedia behavior

Default behavior is intentionally conservative:

- Descriptive User-Agent: `MestizoFaceHarvester/1.0 (<repository URL>; contact: <identifier>)`
- One image request at a time; no parallel image downloads
- 2-second default delay between image requests
- ~500-pixel thumbnails requested through the Wikimedia Commons API
- HTTP `Retry-After` honored
- Exponential/stepped backoff for 429 and temporary 5xx responses: 60, 120, 300, 600 seconds
- Graceful stop after repeated consecutive 429 responses
- No proxy rotation, browser spoofing, rate-limit bypass, or robots-policy evasion

The default contact identifier is this repository URL. For better operator contactability, edit `config.yaml` and replace it with an email address or a stable contact page you control.

## Required files

- `src/collect.py` — orchestration, exact 50-row test sampling, resumability, summaries
- `src/download.py` — Commons API metadata, serial downloading, retry/backoff, Pillow verification, SHA-256
- `src/classify_yunet.py` — YuNet detection at 0/90/180/270°, dominant-face selection, coarse yaw
- `src/package_results.py` — organization, contact sheets, checkpoint ZIP, Release ZIP upload
- `.github/workflows/harvest.yml` — GitHub Actions runner
- `config.yaml`
- `requirements.txt`
- `output/download_manifest.csv`
- `output/classification_manifest.csv`
- `output/regional_summary.csv`
- `output/final_summary.json`

## Face detection and classification

The workflow uses OpenCV YuNet model `face_detection_yunet_2023mar.onnx` with minimum confidence `0.75`.

Every valid image is tested at in-plane rotations `0°`, `90°`, `180°`, and `270°`. The manifest records the face count and maximum confidence for every tested rotation, the chosen rotation, dominant bounding box, dominant landmarks, confidence, face-area fraction, and pose diagnostics.

Coarse head view:

- `front`: absolute estimated yaw ≤ 15°
- `three_quarter`: > 15° and < 55°
- `side`: ≥ 55°

Yaw combines a generic five-landmark PnP estimate with landmark asymmetry and eye/mouth horizontal compression. Because five-point pose is approximate, the pipeline fails closed to `manual_review` if the face is too small, similarly sized competing faces are present, landmark geometry is unstable, or PnP and heuristic pose estimates disagree strongly.

Classification outcomes remain distinct:

- `accepted`
- `manual_review`
- `rejected_no_face`
- `rejected_decode`
- `duplicate_file`
- `download_failed`
- `not_processed`

A failed download is never converted into `rejected_no_face`.

## Run the exact 50-record test

Open **Actions → Wikimedia Commons face harvest → Run workflow**, choose:

- `mode`: `test`
- `delay_seconds`: `2`
- `retry_failed`: `false`

Test mode selects exactly **50 rows**, distributed round-robin across the regions in the CSV. It does not silently substitute a smaller “core” list.

After the run, inspect:

1. `output/final_summary.json` for exact candidate/attempt/verified/accepted/rejected counts.
2. The workflow artifact named `harvest-test-contact-sheets-<run id>`.
3. `output/contact_sheets/test_front.jpg`
4. `output/contact_sheets/test_three_quarter.jpg`
5. `output/contact_sheets/test_side.jpg`
6. `output/contact_sheets/test_manual_review.jpg`

A sheet is omitted if that category has zero images.

Only start the full run after the 50-row test completes successfully and the contact sheets look acceptable.

## Start or resume the full 4,212-record run

Open **Actions → Wikimedia Commons face harvest → Run workflow** and choose:

- `mode`: `full`
- `start_index`: `0` for the first full run
- `delay_seconds`: `2`
- `package_size`: `250`
- `retry_failed`: `false`

Full mode keeps all **4,212 records** in scope. `package_size` controls Release ZIP boundaries; it does not truncate the full dataset.

`start_index` is a zero-based resume/diagnostic override. Normal resumability is manifest-driven: rows already durably completed are skipped.

## Checkpoints and cancellation

After every successfully verified image, both manifests and summaries are written atomically (`.tmp` then `os.replace`).

Durable state is also uploaded to the prerelease tag `wikimedia-harvest-checkpoint`:

- `checkpoint_state.zip`
- cumulative manifests and summary
- finished `harvest_####_####.zip` packages
- test contact sheets when present

On the next workflow run, `checkpoint_state.zip` is restored before processing. Completed Release packages remain intact. A SIGINT/SIGTERM, rate-limit stop, or ordinary workflow failure enters a cleanup path that writes and uploads the current checkpoint. GitHub can forcibly terminate a runner in exceptional cases before cleanup executes; in that case, the last already-uploaded package/checkpoint is the durable resume point.

The GitHub job limit is handled by a 350-minute workflow timeout plus sequential packages. At the default 2-second image spacing, an uninterrupted 4,212-row run is normally below that ceiling unless Wikimedia backoff dominates. Rerunning resumes from persisted manifests.

## Retry only failed downloads

Run the workflow again with:

- `mode`: `full`
- `retry_failed`: `true`

Successful, durably packaged records remain skipped. `download_failed` records become eligible for a new attempt. A failed download is still not treated as a no-face rejection.

## Release packages

Accepted images are organized as:

`organized/accepted/{front|three_quarter|side}/{country}/{region}/{gender_label}/`

Manual-review images are organized as:

`organized/manual_review/{country}/{region}/`

Blank supplied gender uses `unknown`.

Release ZIPs use deterministic candidate ranges, normally 250 records:

- `harvest_0001_0250.zip`
- `harvest_0251_0500.zip`
- …
- final partial range through record 4,212

Each package also contains package-scoped download/classification manifests and `ATTRIBUTION.tsv`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cat data/manifest/expanded_manifest.csv.bz2.b64.part-* | base64 --decode > expanded_manifest.csv.bz2
python - <<'PY'
import bz2, shutil
with bz2.open("expanded_manifest.csv.bz2", "rb") as s, open("expanded_manifest.csv", "wb") as d:
    shutil.copyfileobj(s, d)
PY

python src/collect.py --mode test --delay-seconds 2 --package-size 250
```

For a local full run:

```bash
python src/collect.py \
  --mode full \
  --batch-size 250 \
  --start-index 0 \
  --delay-seconds 2 \
  --package-size 250
```

Release upload is automatically skipped when `GH_TOKEN`/`GITHUB_REPOSITORY` are absent. Local atomic manifests and packages still work.

## Manifest fields

The download manifest preserves the supplied person/birthplace/region/country/scope fields and adds Commons file-page URL, resolved thumbnail URL, original-file URL, license, artist, credit/attribution, HTTP/retry/error fields, verified dimensions/format, SHA-256, duplicate status, local path, timestamp, resume state, and package state.

The classification manifest records face count, confidence, bounding box, landmarks, all tested rotations, selected rotation, face-area fraction, yaw, pose method/diagnostics, view, uncertainty reason, organization path, duplicate/reuse state, and timestamps.

## Verify final counts

Do not infer completion from the number of candidate URLs.

At completion:

1. Confirm `candidate_records_total == 4212`.
2. Confirm `not_processed == 0` after intentionally handling or retrying remaining rows.
3. Reconcile `successfully_verified_image_records` with rows in `output/download_manifest.csv` where `download_status == downloaded` and `sha256` is non-empty.
4. Reconcile `unique_hashes` with the number of distinct SHA-256 values among verified rows.
5. Confirm every released package listed in the manifests exists on the `wikimedia-harvest-checkpoint` Release.
6. Confirm accepted + manual-review + rejections + duplicates/download failures reconcile to the processed candidate records.
7. Treat `download_attempted_records`, verified files, unique hashes, resumed records, failed downloads, accepted classifications, manual review, rejections, and duplicates as separate quantities.

The pipeline never reports 4,212 “downloaded images” merely because 4,212 linked candidates exist.
