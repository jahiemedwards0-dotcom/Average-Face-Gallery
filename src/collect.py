from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import socket
import tempfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.classify_yunet import YuNetClassifier, make_contact_sheet, organize_file
from src.download import RateLimitStop, WikimediaDownloader, sha256_file, utc_now
from src.package_results import package_completed_chunks


DOWNLOAD_EXTRA = [
    "commons_file_page_url", "resolved_thumbnail_url", "original_file_url", "license_name", "license_url",
    "artist", "credit", "attribution", "commons_description_url", "commons_mime", "commons_original_width",
    "commons_original_height", "extmetadata_json", "download_attempted", "download_attempt_count", "download_status", "http_status",
    "retry_count", "error_message", "local_filename", "width", "height", "image_format", "sha256",
    "duplicate_status", "duplicate_of_hash", "download_timestamp", "reused_resumed",
]
CLASS_EXTRA = [
    "classification_status", "face_count", "face_confidence", "dominant_bbox", "tested_rotations",
    "detection_rotation", "estimated_yaw", "yaw_signed", "view_class", "pose_method", "pose_components",
    "uncertainty_reason", "face_area_fraction", "organized_filename",
]


def atomic_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def validate_input(df: pd.DataFrame) -> None:
    required = {
        "candidate_id", "person_qid", "person_url", "person_label", "gender_qid", "gender_label", "birth_date",
        "birth_year", "birthplace_qid", "birthplace_label", "region", "country", "scope_tier", "image_url",
        "commons_filename",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input CSV missing columns: {missing}")
    if df["candidate_id"].astype(str).duplicated().any():
        dups = df.loc[df["candidate_id"].astype(str).duplicated(), "candidate_id"].astype(str).head().tolist()
        raise ValueError(f"candidate_id must be unique; duplicates include {dups}")


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in DOWNLOAD_EXTRA + CLASS_EXTRA:
        if c not in df.columns:
            if c == "download_attempted":
                df[c] = False
            elif c in {"retry_count", "download_attempt_count"}:
                df[c] = 0
            elif c == "download_status":
                df[c] = "not_processed"
            elif c == "classification_status":
                df[c] = "not_processed"
            elif c == "duplicate_status":
                df[c] = ""
            elif c == "reused_resumed":
                df[c] = False
            else:
                df[c] = ""
    return df


def load_or_initialize(input_path: Path, output_path: Path) -> pd.DataFrame:
    source = pd.read_csv(input_path, keep_default_na=False)
    validate_input(source)
    if output_path.exists():
        existing = pd.read_csv(output_path, keep_default_na=False)
        validate_input(existing)
        if len(existing) != len(source) or existing["candidate_id"].astype(str).tolist() != source["candidate_id"].astype(str).tolist():
            raise ValueError("Existing manifest does not match input candidate order/IDs; refusing unsafe resume")
        # Refresh original source columns, preserve pipeline columns.
        for c in source.columns:
            existing[c] = source[c]
        return ensure_columns(existing)
    return ensure_columns(source.copy())


def deterministic_test_indices(df: pd.DataFrame, n: int = 50) -> list[int]:
    if len(df) < n:
        raise ValueError(f"Test mode requires exactly {n} records; input has only {len(df)}")
    groups: dict[str, deque[int]] = {}
    # Round-robin over region in first-seen order, but spread within each region rather than taking adjacent rows.
    for region, group in df.groupby("region", sort=False):
        idx = group.index.tolist()
        if len(idx) > 1:
            # Interleave from evenly spaced positions to reduce local ordering bias.
            order = sorted(set(int(round(x)) for x in [i * (len(idx)-1) / max(1, min(len(idx), n)-1) for i in range(min(len(idx), n))]))
            sampled = [idx[i] for i in order]
            leftovers = [x for x in idx if x not in sampled]
            idx = sampled + leftovers
        groups[str(region)] = deque(idx)
    keys = list(groups)
    selected: list[int] = []
    while len(selected) < n:
        progressed = False
        for key in keys:
            if groups[key] and len(selected) < n:
                selected.append(groups[key].popleft())
                progressed = True
        if not progressed:
            break
    if len(selected) != n:
        raise RuntimeError(f"Could only select {len(selected)} test records")
    return selected


def existing_hash_index(df: pd.DataFrame) -> dict[str, str]:
    result: dict[str, str] = {}
    for _, row in df.iterrows():
        digest = str(row.get("sha256") or "")
        local = str(row.get("local_filename") or "")
        if digest and local and Path(local).exists():
            try:
                if sha256_file(Path(local)) == digest:
                    result.setdefault(digest, local)
            except OSError:
                pass
    return result


def row_is_verified_and_reusable(row: pd.Series) -> bool:
    status = str(row.get("download_status") or "")
    digest = str(row.get("sha256") or "")
    local = str(row.get("local_filename") or "")
    if status not in {"verified", "verified_duplicate"} or not digest or not local:
        return False
    path = Path(local)
    if not path.exists():
        return False
    try:
        return sha256_file(path) == digest
    except OSError:
        return False


def copy_download_to_classification(download_df: pd.DataFrame) -> pd.DataFrame:
    return ensure_columns(download_df.copy())


def write_summaries(df: pd.DataFrame, output_dir: Path, *, mode: str, scope_indices: list[int]) -> dict[str, Any]:
    rows = []
    for (country, region), group in df.groupby(["country", "region"], sort=False, dropna=False):
        verified = group["download_status"].isin(["verified", "verified_duplicate"])
        rows.append({
            "country": country,
            "region": region,
            "csv_candidates": len(group),
            "successfully_downloaded": int(verified.sum()),
            "download_failures": int((group["download_status"] == "download_failed").sum()),
            "unique_hashes": int(group.loc[group["sha256"].astype(str) != "", "sha256"].nunique()),
            "accepted_front": int(((group["classification_status"] == "accepted") & (group["view_class"] == "front")).sum()),
            "accepted_three_quarter": int(((group["classification_status"] == "accepted") & (group["view_class"] == "three_quarter")).sum()),
            "accepted_side": int(((group["classification_status"] == "accepted") & (group["view_class"] == "side")).sum()),
            "manual_review": int((group["classification_status"] == "manual_review").sum()),
            "rejected_no_face": int((group["classification_status"] == "rejected_no_face").sum()),
            "unknown_gender_count": int(group["gender_label"].astype(str).str.strip().eq("").sum()),
        })
    regional = pd.DataFrame(rows)
    atomic_csv(regional, output_dir / "regional_summary.csv")

    scope = df.loc[scope_indices] if scope_indices else df.iloc[0:0]
    report = scope if mode == "test" else df
    attempted = pd.to_numeric(report["download_attempt_count"], errors="coerce").fillna(0).sum()
    candidate_records_attempted = report["download_attempted"].astype(str).str.lower().isin(["true", "1"]).sum()
    verified_mask = report["download_status"].isin(["verified", "verified_duplicate"])
    unique_hashes = report.loc[report["sha256"].astype(str) != "", "sha256"].nunique()
    accepted = int((report["classification_status"] == "accepted").sum())
    manual = int((report["classification_status"] == "manual_review").sum())
    rejected_no_face = int((report["classification_status"] == "rejected_no_face").sum())
    rejected_decode = int((report["classification_status"] == "rejected_decode").sum())
    duplicate = int((report["classification_status"] == "duplicate_file").sum())
    download_failed = int((report["classification_status"] == "download_failed").sum())
    reused = int(report["reused_resumed"].astype(str).str.lower().isin(["true", "1"]).sum())
    summary = {
        "mode": mode,
        "candidate_records": int(len(df)),
        "scope_records": int(len(scope)),
        "download_attempts": int(attempted),
        "candidate_records_attempted": int(candidate_records_attempted),
        "successfully_verified_image_records": int(verified_mask.sum()),
        "unique_hashes_in_scope": int(unique_hashes),
        "reused_resumed_files": reused,
        "failed_downloads": int((report["download_status"] == "download_failed").sum()),
        "accepted_classifications": accepted,
        "accepted_front": int(((report["classification_status"] == "accepted") & (report["view_class"] == "front")).sum()),
        "accepted_three_quarter": int(((report["classification_status"] == "accepted") & (report["view_class"] == "three_quarter")).sum()),
        "accepted_side": int(((report["classification_status"] == "accepted") & (report["view_class"] == "side")).sum()),
        "manual_review_cases": manual,
        "rejections": rejected_no_face + rejected_decode,
        "rejected_no_face": rejected_no_face,
        "rejected_decode": rejected_decode,
        "duplicates": duplicate,
        "download_failed_classification_outcomes": download_failed,
        "generated_at": utc_now(),
    }
    atomic_json(summary, output_dir / "final_summary.json")
    return summary


def build_contact_sheets(df: pd.DataFrame, output_dir: Path, scope_indices: list[int]) -> None:
    scope = df.loc[scope_indices]
    categories = {
        "front": scope[(scope["classification_status"] == "accepted") & (scope["view_class"] == "front")],
        "three_quarter": scope[(scope["classification_status"] == "accepted") & (scope["view_class"] == "three_quarter")],
        "side": scope[(scope["classification_status"] == "accepted") & (scope["view_class"] == "side")],
        "manual_review": scope[scope["classification_status"] == "manual_review"],
    }
    for name, sub in categories.items():
        make_contact_sheet(sub.to_dict("records"), name.replace("_", " ").title(), output_dir / "contact_sheets" / f"{name}.jpg")


def main() -> int:
    ap = argparse.ArgumentParser(description="Resumable Wikimedia Commons face-view harvester")
    ap.add_argument("--input", default="data/expanded_manifest.csv")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--mode", choices=["test", "full"], required=True)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--start-index", type=int, default=0)
    ap.add_argument("--delay-seconds", type=float, default=None)
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--package-size", type=int, default=None)
    ap.add_argument("--repo-url", default=None)
    ap.add_argument("--contact", default=None)
    ap.add_argument("--output-dir", default="output")
    ap.add_argument("--downloads-dir", default="downloads/unique")
    ap.add_argument("--organized-dir", default="organized")
    ap.add_argument("--model", default="models/face_detection_yunet_2023mar.onnx")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    download_manifest_path = output_dir / "download_manifest.csv"
    classification_manifest_path = output_dir / "classification_manifest.csv"
    manifest_path = classification_manifest_path if classification_manifest_path.exists() else download_manifest_path
    df = load_or_initialize(Path(args.input), manifest_path)
    # Ensure both manifests exist from the start and contain all 4,212 rows (or whatever the validated input has).
    atomic_csv(df, download_manifest_path)
    atomic_csv(df, classification_manifest_path)

    if args.mode == "full" and not (output_dir / "test_success.json").exists():
        raise SystemExit("Full mode blocked: output/test_success.json is absent. Complete a successful 50-record test first.")

    test_indices = deterministic_test_indices(df, 50)
    if args.mode == "test":
        scope_indices = test_indices
        pd.DataFrame({"manifest_index": scope_indices, "candidate_id": df.loc[scope_indices, "candidate_id"].tolist(), "region": df.loc[scope_indices, "region"].tolist(), "country": df.loc[scope_indices, "country"].tolist()}).to_csv(output_dir / "test_selection.csv", index=False)
    else:
        scope_indices = list(df.index[max(0, args.start_index):])

    batch_size = args.batch_size if args.batch_size is not None else int(cfg["run"]["batch_size"])
    if args.mode == "test":
        batch_size = 50
    delay = args.delay_seconds if args.delay_seconds is not None else float(cfg["wikimedia"]["delay_seconds"])
    package_size = args.package_size if args.package_size is not None else int(cfg["packaging"]["package_size"])
    if batch_size <= 0:
        raise SystemExit("batch_size must be positive")
    if not 250 <= package_size <= 500:
        raise SystemExit("package_size must be between 250 and 500 records")
    if delay < 0:
        raise SystemExit("delay_seconds must be non-negative")
    repo_url = args.repo_url or os.getenv("HARVEST_REPOSITORY_URL") or cfg["wikimedia"]["repository_url"]
    contact = args.contact or os.getenv("WIKIMEDIA_CONTACT") or cfg["wikimedia"].get("contact", "")
    if "OWNER/REPOSITORY" in repo_url and args.mode == "full":
        raise SystemExit("Set a real repository URL before full mode; placeholder OWNER/REPOSITORY is not an acceptable Wikimedia identifier.")
    if args.mode == "full" and not contact:
        raise SystemExit("Set WIKIMEDIA_CONTACT or --contact before full mode.")

    # Fast infrastructure preflight. In test mode an unavailable Commons host is recorded
    # against all 50 selected test records so the result is exact and visibly failed. In full
    # mode no candidate statuses are mutated; the job can be rerun without retry flags.
    network_preflight_error = ""
    try:
        socket.getaddrinfo("commons.wikimedia.org", 443)
    except OSError as exc:
        network_preflight_error = f"Network preflight failed for commons.wikimedia.org: {type(exc).__name__}: {exc}"

    downloader = WikimediaDownloader(
        repo_url=repo_url,
        contact=contact,
        thumbnail_width=int(cfg["wikimedia"]["thumbnail_width"]),
        delay_seconds=delay,
        timeout_seconds=int(cfg["wikimedia"]["timeout_seconds"]),
        backoff_waits=cfg["wikimedia"]["backoff_waits_seconds"],
        max_consecutive_429=int(cfg["wikimedia"]["max_consecutive_429"]),
    )
    known_hashes = existing_hash_index(df)
    classifier: YuNetClassifier | None = None
    model_path = Path(args.model)
    if model_path.exists():
        classifier = YuNetClassifier(
            model_path,
            min_confidence=float(cfg["face_detection"]["min_confidence"]),
            min_face_px=int(cfg["face_detection"]["min_face_px"]),
            min_face_area_fraction=float(cfg["face_detection"]["min_face_area_fraction"]),
            similar_face_ratio=float(cfg["face_detection"]["similar_face_ratio"]),
        )

    attempted_this_run = 0
    infrastructure_error = network_preflight_error
    rate_stop = False

    if network_preflight_error and args.mode == "test":
        for idx in scope_indices:
            df.at[idx, "download_attempted"] = True
            df.at[idx, "download_attempt_count"] = int(pd.to_numeric(df.at[idx, "download_attempt_count"], errors="coerce") or 0) + 1
            df.at[idx, "download_status"] = "download_failed"
            df.at[idx, "classification_status"] = "download_failed"
            df.at[idx, "error_message"] = network_preflight_error
            atomic_csv(df, download_manifest_path)
            atomic_csv(df, classification_manifest_path)
            attempted_this_run += 1

    indices_to_process = [] if network_preflight_error else scope_indices
    eligible_indices: list[int] = []
    for idx in indices_to_process:
        row = df.loc[idx]
        current_status = str(row.get("classification_status") or "")
        if current_status in {"accepted", "manual_review", "rejected_no_face", "rejected_decode", "duplicate_file"}:
            if str(row.get("download_status")) in {"verified", "verified_duplicate"}:
                local = Path(str(row.get("local_filename") or ""))
                digest = str(row.get("sha256") or "")
                if local.exists() and digest and sha256_file(local) == digest:
                    df.at[idx, "reused_resumed"] = True
                    continue
                if str(row.get("organized_filename") or ""):
                    # Durable package/checkpoint already owns the bytes; do not redownload merely
                    # because a runner-local path no longer exists.
                    df.at[idx, "reused_resumed"] = True
                    continue
            else:
                continue
        if str(row.get("download_status")) == "download_failed" and not (args.retry_failed or args.mode == "test"):
            continue
        eligible_indices.append(idx)
        if len(eligible_indices) >= batch_size:
            break

    metadata_batch_size = max(1, min(50, int(cfg["wikimedia"].get("metadata_batch_size", 10))))
    stop_processing = False
    for batch_start in range(0, len(eligible_indices), metadata_batch_size):
        batch_indices = eligible_indices[batch_start:batch_start + metadata_batch_size]
        filenames = [str(df.at[idx, "commons_filename"] or "").strip() for idx in batch_indices]
        try:
            metadata_by_filename = downloader.resolve_commons_metadata_batch(filenames)
        except RateLimitStop as exc:
            rate_stop = True
            infrastructure_error = str(exc)
            atomic_csv(df, download_manifest_path)
            atomic_csv(df, classification_manifest_path)
            break

        for idx, filename in zip(batch_indices, filenames):
            attempted_this_run += 1
            df.at[idx, "download_attempted"] = True
            current_attempts = pd.to_numeric(df.at[idx, "download_attempt_count"], errors="coerce")
            df.at[idx, "download_attempt_count"] = (0 if pd.isna(current_attempts) else int(current_attempts)) + 1
            atomic_csv(df, download_manifest_path)

            try:
                result = downloader.download_one(
                    df.loc[idx].to_dict(),
                    unique_dir=Path(args.downloads_dir),
                    known_hashes=known_hashes,
                    metadata=metadata_by_filename.get(filename),
                )
            except RateLimitStop as exc:
                df.at[idx, "download_status"] = "download_failed"
                df.at[idx, "classification_status"] = "download_failed"
                df.at[idx, "error_message"] = str(exc)
                rate_stop = True
                infrastructure_error = str(exc)
                atomic_csv(df, download_manifest_path)
                atomic_csv(df, classification_manifest_path)
                stop_processing = True
                break

            for key, value in result.values.items():
                if key in df.columns:
                    df.at[idx, key] = value
            dstatus = str(df.at[idx, "download_status"])
            if dstatus == "verified_duplicate":
                df.at[idx, "classification_status"] = "duplicate_file"
            elif dstatus == "rejected_decode":
                df.at[idx, "classification_status"] = "rejected_decode"
            elif dstatus != "verified":
                df.at[idx, "classification_status"] = "download_failed"
            atomic_csv(df, download_manifest_path)

            if dstatus == "verified":
                if classifier is None:
                    df.at[idx, "classification_status"] = "not_processed"
                    infrastructure_error = f"YuNet model missing: {model_path}"
                    stop_processing = True
                else:
                    local = Path(str(df.at[idx, "local_filename"]))
                    class_result = classifier.classify(local)
                    for key, value in class_result.items():
                        if key in df.columns:
                            df.at[idx, key] = value
                    organized = organize_file(local, df.loc[idx].to_dict(), class_result, Path(args.organized_dir))
                    df.at[idx, "organized_filename"] = organized
            atomic_csv(df, classification_manifest_path)
            if stop_processing:
                break
        if stop_processing:
            break

    # Always sync download manifest with current download fields after classifications.
    atomic_csv(df, download_manifest_path)
    atomic_csv(df, classification_manifest_path)
    if args.mode == "test":
        build_contact_sheets(df, output_dir, scope_indices)
    summary = write_summaries(df, output_dir, mode=args.mode, scope_indices=scope_indices)

    test_success = False
    if args.mode == "test":
        scope = df.loc[scope_indices]
        all_terminal = scope["classification_status"].isin({"accepted", "manual_review", "rejected_no_face", "rejected_decode", "duplicate_file", "download_failed"}).all()
        verified = int(scope["download_status"].isin(["verified", "verified_duplicate"]).sum())
        classified_or_dup = int(scope["classification_status"].isin(["accepted", "manual_review", "rejected_no_face", "rejected_decode", "duplicate_file"]).sum())
        test_success = bool(all_terminal and verified > 0 and classified_or_dup > 0 and not infrastructure_error and not rate_stop)
        if test_success:
            atomic_json({"success": True, "completed_at": utc_now(), "selection_count": 50, "summary": summary}, output_dir / "test_success.json")
        else:
            (output_dir / "test_success.json").unlink(missing_ok=True)
            atomic_json({
                "success": False,
                "completed_at": utc_now(),
                "selection_count": 50,
                "infrastructure_error": infrastructure_error,
                "rate_limit_stop": rate_stop,
                "summary": summary,
            }, output_dir / "test_result.json")

    package_completed_chunks(classification_manifest_path, output_dir, Path("packages"), package_size)
    print(json.dumps({"summary": summary, "test_success": test_success, "infrastructure_error": infrastructure_error, "rate_limit_stop": rate_stop}, indent=2))
    if args.mode == "full":
        return 3 if (infrastructure_error or rate_stop) else 0
    return 0 if test_success else 2


if __name__ == "__main__":
    raise SystemExit(main())
