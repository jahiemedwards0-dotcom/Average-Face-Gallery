from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd
from PIL import Image

from src.classify_yunet import estimate_yaw_from_yunet
from src.collect import deterministic_test_indices
from src.download import WikimediaDownloader
from src.package_results import package_completed_chunks


class _Raw:
    closed = False


class _Response:
    def __init__(self, *, status=200, payload=None, data=b"", headers=None):
        self.status_code = status
        self._payload = payload
        self.data = data
        self.headers = headers or {}
        self.text = ""
        self.raw = _Raw()

    def json(self):
        return self._payload

    def iter_content(self, chunk_size=1):
        yield self.data


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class PipelineTests(unittest.TestCase):
    def test_distributed_selection_is_exactly_50(self):
        df = pd.read_csv("data/expanded_manifest.csv", keep_default_na=False)
        indices = deterministic_test_indices(df, 50)
        self.assertEqual(len(indices), 50)
        self.assertEqual(len(set(indices)), 50)
        self.assertGreaterEqual(df.loc[indices, "region"].nunique(), 2)

    def test_pose_threshold_fixtures(self):
        front = np.array([0, 0, 100, 120, 30, 40, 70, 40, 50, 65, 35, 90, 65, 90, 0.95], float)
        quarter = np.array([0, 0, 100, 120, 25, 40, 65, 40, 60, 65, 30, 90, 60, 90, 0.95], float)
        side = np.array([0, 0, 100, 120, 15, 40, 45, 40, 75, 65, 20, 90, 55, 90, 0.95], float)
        self.assertEqual(estimate_yaw_from_yunet(front).view, "front")
        self.assertEqual(estimate_yaw_from_yunet(quarter).view, "three_quarter")
        self.assertEqual(estimate_yaw_from_yunet(side).view, "side")

    def test_metadata_validation_and_exact_dedup(self):
        ext = {
            "LicenseShortName": {"value": "CC BY 4.0"},
            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
            "Artist": {"value": "Test Artist"},
            "Credit": {"value": "Test Credit"},
        }
        payload = {
            "query": {
                "pages": [
                    {"title": "File:A.jpg", "imageinfo": [{"url": "https://upload.wikimedia.org/a.jpg", "thumburl": "https://upload.wikimedia.org/a-500.jpg", "descriptionurl": "https://commons.wikimedia.org/wiki/File:A.jpg", "mime": "image/jpeg", "width": 1000, "height": 800, "extmetadata": ext}]},
                    {"title": "File:B.jpg", "imageinfo": [{"url": "https://upload.wikimedia.org/b.jpg", "thumburl": "https://upload.wikimedia.org/b-500.jpg", "descriptionurl": "https://commons.wikimedia.org/wiki/File:B.jpg", "mime": "image/jpeg", "width": 1000, "height": 800, "extmetadata": ext}]},
                ]
            }
        }
        image = Image.new("RGB", (120, 100), "white")
        buf = BytesIO()
        image.save(buf, format="JPEG")
        data = buf.getvalue()
        session = _Session([_Response(payload=payload), _Response(data=data), _Response(data=data)])
        downloader = WikimediaDownloader(repo_url="https://github.com/o/r", contact="x@example.com", delay_seconds=0, session=session)
        metadata = downloader.resolve_commons_metadata_batch(["A.jpg", "B.jpg"])
        self.assertTrue(metadata["A.jpg"]["ok"])
        self.assertTrue(metadata["B.jpg"]["ok"])
        with TemporaryDirectory() as td:
            known = {}
            first = downloader.download_one({"commons_filename": "A.jpg"}, unique_dir=Path(td), known_hashes=known, metadata=metadata["A.jpg"]).values
            second = downloader.download_one({"commons_filename": "B.jpg"}, unique_dir=Path(td), known_hashes=known, metadata=metadata["B.jpg"]).values
            self.assertEqual(first["download_status"], "verified")
            self.assertEqual(second["download_status"], "verified_duplicate")
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(len(list(Path(td).glob("*"))), 1)

    def test_250_record_package_contains_one_copy_per_hash(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            image = root / "x.jpg"
            Image.new("RGB", (30, 30), "white").save(image)
            rows = []
            for i in range(250):
                rows.append({
                    "candidate_id": f"C{i+1:04d}",
                    "classification_status": "accepted",
                    "download_status": "verified",
                    "sha256": "same-hash" if i < 2 else "",
                    "local_filename": str(image) if i < 2 else "",
                    "organized_filename": "",
                })
            manifest = root / "manifest.csv"
            pd.DataFrame(rows).to_csv(manifest, index=False)
            made = package_completed_chunks(manifest, root, root / "packages", 250)
            self.assertEqual([p.name for p in made], ["harvest_0001_0250.zip"])
            with zipfile.ZipFile(made[0]) as zf:
                self.assertEqual(len(pd.read_csv(zf.open("manifest.csv"))), 250)
                self.assertEqual(sum(name.startswith("images/") for name in zf.namelist()), 1)


if __name__ == "__main__":
    unittest.main()
