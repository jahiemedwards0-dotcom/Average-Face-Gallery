from __future__ import annotations

import argparse
import csv
import bz2
import hashlib
import json
import os
import shutil
import signal
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
import yaml

from classify_yunet import YuNetClassifier
from download import StopForRateLimit, WikimediaClient, derive_commons_filename, sha256_file, utc_now
from package_results import (
    make_checkpoint_zip,
    make_package,
    organize_image,
    restore_release_package_images,
    upload_release_assets,
    write_contact_sheet,
)


DOWNLOAD_EXTRA_FIELDS = [
    "commons_file_page_url", "resolved_thumbnail_url", "original_file_url",
    "source", "license_name", "license_url", "artist", "credit", "attribution", "usage_terms",
    "metadata_status", "metadata_http_status", "metadata_retry_count",
    "download_status", "http_status", "retry_count", "error_message",
    "local_filename", "width", "height", "image_format", "sha256",
    "duplicate_status", "duplicate_of_hash", "duplicate_of_candidate_id",
    "download_timestamp", "resume_reused", "package_asset", "package_released",
]
CLASS_EXTRA_FIELDS = [
    "classification_status", "face_count", "confidence", "dominant_bbox", "dominant_landmarks",
    "tested_rotations", "selected_rotation", "face_area_fraction", "estimated_yaw", "abs_yaw",
    "view", "pose_method", "pose_metrics", "pnp_yaw", "pose_disagreement_deg",
    "pose_uncertainty_reason", "organized_filename", "duplicate_of_candidate_id",
    "reused_classification_candidate_id", "classification_timestamp", "resume_reused",
    "package_asset", "package_released",
]


STOP_REQUESTED = [False]


def _signal_handler(signum, frame):
    STOP_REQUESTED[0] = True
    print(f"[checkpoint] received signal {signum}; stopping after current atomic operation", flush=True)


for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _signal_handler)


def read_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def atomic_write_csv(rows: List[Dict[str, Any]], path: Path, fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_manifest(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return {str(r["candidate_id"]): r for r in csv.DictReader(f) if r.get("candidate_id")}
    except Exception:
        return {}


def ensure_input_csv(input_path: Path, compressed_path: Path) -> None:
    if input_path.exists():
        return
    if not compressed_path.exists():
        raise FileNotFoundError(f"Missing {input_path} and {compressed_path}")
    with bz2.open(compressed_path, "rb") as src, input_path.open("wb") as dst:
        shutil.copyfileobj(src, dst)


def exact_test_indices(df: pd.DataFrame, n: int = 50) -> List[int]:
    if len(df) < n:
        raise ValueError(f"Test mode requires exactly {n} rows but manifest has {len(df)}")
    groups = defaultdict(list)
    for idx, region in enumerate(df["region"].fillna("unknown").astype(str)):
        groups[region].append(idx)
    regions = sorted(groups)
    selected: List[int] = []
    depth = 0
    while len(selected) < n:
        progressed = False
        for region in regions:
            if depth < len(groups[region]):
                selected.append(groups[region][depth])
                progressed = True
                if len(selected) == n:
                    break
        if not progressed:
            break
        depth += 1
    if len(selected) != n:
        raise RuntimeError("Could not construct exactly 50 distributed test rows")
    return selected


def init_rows(df: pd.DataFrame, existing: Dict[str, Dict[str, str]], extras: List[str], status_field: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    base_fields = list(df.columns)
    fields = base_fields + [f for f in extras if f not in base_fields]
    rows: List[Dict[str, Any]] = []
    for idx, sr in df.iterrows():
        base = {k: ("" if pd.isna(v) else v) for k, v in sr.to_dict().items()}
        cid = str(base["candidate_id"])
        old = existing.get(cid, {})
        merged = {**base}
        for f in extras:
            merged[f] = old.get(f, "")
        if not merged.get(status_field):
            merged[status_field] = "not_processed"
        merged["_row_number"] = idx + 1
        rows.append(merged)
    return rows, fields


def download_is_durably_reusable(row: Dict[str, Any]) -> bool:
    if row.get("download_status") != "downloaded" or not row.get("sha256"):
        return False
    path = Path(str(row.get("local_filename") or ""))
    if path.exists():
        try:
            return sha256_file(path) == row.get("sha256")
        except OSError:
            return False
    return str(row.get("package_released", "")).lower() in {"true", "1", "yes"}


def class_is_reusable(row: Dict[str, Any]) -> bool:
    return row.get("classification_status") in {
        "accepted", "manual_review", "rejected_no_face", "rejected_decode", "duplicate_file"
    }



TERMINAL_CLASS_STATUSES = {
    "accepted", "manual_review", "rejected_no_face", "rejected_decode",
    "duplicate_file", "download_failed"
}


def range_is_complete(class_rows: List[Dict[str, Any]], start_1based: int, end_1based: int) -> bool:
    members = [r for r in class_rows if start_1based <= int(r["_row_number"]) <= end_1based]
    return bool(members) and all(r.get("classification_status") in TERMINAL_CLASS_STATUSES for r in members)


def mark_package_released(download_rows, class_rows, start_1based, end_1based, asset_name):
    for rows in (download_rows, class_rows):
        for r in rows:
            rn = int(r["_row_number"])
            if start_1based <= rn <= end_1based:
                r["package_asset"] = asset_name
                r["package_released"] = True


def prune_released_range(download_rows, class_rows, start_1based, end_1based):
    seen = set()
    for r in download_rows:
        rn = int(r["_row_number"])
        if start_1based <= rn <= end_1based:
            path = str(r.get("local_filename") or "")
            if path and path not in seen:
                seen.add(path)
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
    for r in class_rows:
        rn = int(r["_row_number"])
        if start_1based <= rn <= end_1based:
            path = str(r.get("organized_filename") or "")
            if path and path not in seen:
                seen.add(path)
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass


def durable_checkpoint(output_dir: Path, download_dir: Path, organized_root: Path, package_dir: Path, release_tag: str) -> None:
    checkpoint = make_checkpoint_zip(
        [output_dir, download_dir, organized_root],
        package_dir / "checkpoint_state.zip",
        Path("."),
    )
    upload_release_assets(
        [checkpoint, output_dir / "download_manifest.csv", output_dir / "classification_manifest.csv",
         output_dir / "regional_summary.csv", output_dir / "final_summary.json",
         output_dir / "test_gate.json"],
        release_tag,
    )


def ensure_model(model_path: Path, url: str) -> None:
    if model_path.exists() and model_path.stat().st_size > 100_000:
        return
    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[model] downloading YuNet model from {url}", flush=True)
    r = requests.get(url, timeout=60, headers={"User-Agent": "MestizoFaceHarvester/1.0"})
    r.raise_for_status()
    tmp = model_path.with_suffix(".tmp")
    tmp.write_bytes(r.content)
    os.replace(tmp, model_path)


def summary_counts(download_rows: List[Dict[str, Any]], class_rows: List[Dict[str, Any]], candidate_scope: int, mode: str) -> Dict[str, Any]:
    dl = Counter(r.get("download_status") or "not_processed" for r in download_rows)
    cl = Counter(r.get("classification_status") or "not_processed" for r in class_rows)
    verified = [r for r in download_rows if r.get("download_status") == "downloaded" and r.get("sha256")]
    unique_hashes = len({r.get("sha256") for r in verified if r.get("sha256")})
    candidate_attempts = sum(1 for r in download_rows if r.get("http_status") or (r.get("download_status") not in {"", "not_processed"}))
    return {
        "mode": mode,
        "candidate_records_total": len(download_rows),
        "candidate_records_in_current_scope": candidate_scope,
        "download_attempts": candidate_attempts,
        "download_attempted_records": candidate_attempts,
        "successfully_verified_image_files": len(verified),
        "successfully_verified_image_records": len(verified),
        "unique_hashes": unique_hashes,
        "reused_resumed_records": sum(str(r.get("resume_reused", "")).lower() in {"true", "1"} for r in download_rows),
        "failed_downloads": dl["download_failed"],
        "rejected_decode": dl["rejected_decode"] + cl["rejected_decode"],
        "duplicates": sum(bool(r.get("duplicate_status")) for r in download_rows),
        "accepted_classifications": cl["accepted"],
        "accepted_front": sum(r.get("classification_status") == "accepted" and r.get("view") == "front" for r in class_rows),
        "accepted_three_quarter": sum(r.get("classification_status") == "accepted" and r.get("view") == "three_quarter" for r in class_rows),
        "accepted_side": sum(r.get("classification_status") == "accepted" and r.get("view") == "side" for r in class_rows),
        "manual_review": cl["manual_review"],
        "rejected_no_face": cl["rejected_no_face"],
        "rejections": cl["rejected_no_face"] + dl["rejected_decode"] + cl["rejected_decode"],
        "duplicate_file": cl["duplicate_file"],
        "not_processed": cl["not_processed"],
        "generated_at": utc_now(),
    }


def write_regional_summary(df: pd.DataFrame, download_rows: List[Dict[str, Any]], class_rows: List[Dict[str, Any]], path: Path) -> None:
    d = {str(r["candidate_id"]): r for r in download_rows}
    c = {str(r["candidate_id"]): r for r in class_rows}
    out = []
    for region, g in df.groupby(df["region"].fillna("unknown"), dropna=False):
        ids = [str(x) for x in g["candidate_id"]]
        dr = [d[i] for i in ids]
        cr = [c[i] for i in ids]
        verified = [r for r in dr if r.get("download_status") == "downloaded" and r.get("sha256")]
        out.append({
            "region": region,
            "country": "; ".join(sorted(set(g["country"].fillna("unknown").astype(str)))),
            "csv_candidates": len(ids),
            "successfully_downloaded": len(verified),
            "download_failures": sum(r.get("download_status") == "download_failed" for r in dr),
            "unique_hashes": len({r.get("sha256") for r in verified}),
            "accepted_front": sum(r.get("classification_status") == "accepted" and r.get("view") == "front" for r in cr),
            "accepted_three_quarter": sum(r.get("classification_status") == "accepted" and r.get("view") == "three_quarter" for r in cr),
            "accepted_side": sum(r.get("classification_status") == "accepted" and r.get("view") == "side" for r in cr),
            "manual_review": sum(r.get("classification_status") == "manual_review" for r in cr),
            "rejected_no_face": sum(r.get("classification_status") == "rejected_no_face" for r in cr),
            "unknown_gender_count": sum(str(r.get("gender_label") or "").strip().lower() in {"", "nan", "unknown"} for r in dr),
        })
    pd.DataFrame(out).sort_values(["country", "region"]).to_csv(path, index=False)


def persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, mode, scope_count):
    atomic_write_csv(download_rows, output_dir / "download_manifest.csv", download_fields)
    atomic_write_csv(class_rows, output_dir / "classification_manifest.csv", class_fields)
    write_regional_summary(df, download_rows, class_rows, output_dir / "regional_summary.csv")
    summary = summary_counts(download_rows, class_rows, scope_count, mode)
    atomic_write_json(summary, output_dir / "final_summary.json")
    return summary


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["test", "full"], required=True)
    p.add_argument("--batch-size", type=int, default=250)
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--delay-seconds", type=float, default=2.0)
    p.add_argument("--retry-failed", action="store_true")
    p.add_argument("--package-size", type=int, default=250)
    p.add_argument("--config", default="config.yaml")
    return p.parse_args()
