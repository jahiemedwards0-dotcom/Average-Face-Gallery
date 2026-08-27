#!/usr/bin/env bash
set -euo pipefail

cat \
  data/manifest/expanded_manifest.csv.bz2.b64.part-01 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-02 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-03 \
  data/manifest/repair-part-04-01 \
  data/manifest/repair-part-04-02 \
  data/manifest/repair-part-04-03 \
  data/manifest/repair-part-04-04 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-05 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-06 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-07 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-08 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-09 \
  data/manifest/repair-part-10-01a \
  data/manifest/repair-part-10-01b \
  data/manifest/repair-part-10-02 \
  data/manifest/repair-part-10-03 \
  data/manifest/repair-part-10-04 \
  data/manifest/expanded_manifest.csv.bz2.b64.part-11 \
  data/manifest/repair-part-12-01 \
  data/manifest/repair-part-12-02 \
  data/manifest/repair-part-12-03 \
  > expanded_manifest.csv.bz2.b64

base64 --decode expanded_manifest.csv.bz2.b64 > expanded_manifest.csv.bz2
