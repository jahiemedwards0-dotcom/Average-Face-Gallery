from collect_support import *

def main() -> int:
    args = parse_args()
    cfg = read_config(Path(args.config))
    paths = cfg["paths"]
    input_csv = Path(paths["input_csv"])
    ensure_input_csv(input_csv, Path(paths["input_compressed"]))
    output_dir = Path(paths["output_dir"])
    download_dir = Path(paths["download_dir"])
    organized_root = Path(paths["organized_dir"])
    package_dir = Path(paths["package_dir"])
    contact_dir = Path(paths["contact_sheet_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv)
    if len(df) != 4212:
        raise RuntimeError(f"Expected exactly 4,212 candidate records, found {len(df)}")
    if df["candidate_id"].astype(str).duplicated().any():
        raise RuntimeError("candidate_id must be unique")

    existing_d = load_manifest(output_dir / "download_manifest.csv")
    existing_c = load_manifest(output_dir / "classification_manifest.csv")
    download_rows, download_fields = init_rows(df, existing_d, DOWNLOAD_EXTRA_FIELDS, "download_status")
    class_rows, class_fields = init_rows(df, existing_c, CLASS_EXTRA_FIELDS, "classification_status")
    d_by_id = {str(r["candidate_id"]): r for r in download_rows}
    c_by_id = {str(r["candidate_id"]): r for r in class_rows}

    if args.mode == "test":
        target_indices = exact_test_indices(df, 50)
        if len(target_indices) != 50:
            raise AssertionError("test mode must target exactly 50 rows")
    else:
        gate_path = output_dir / "test_gate.json"
        if not gate_path.exists():
            raise RuntimeError("Full mode is blocked until the exact 50-record test completes successfully.")
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Invalid test gate: {exc}") from exc
        if gate.get("completed") is not True or gate.get("candidate_scope") != 50:
            raise RuntimeError("Full mode is blocked: the 50-record test gate is incomplete.")
        start = max(0, args.start_index)
        target_indices = list(range(start, len(df)))
        # batch_size controls durable checkpoint cadence; it never truncates full mode.

    scope_count = len(target_indices)
    persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)

    repo_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/" + os.environ.get(
        "GITHUB_REPOSITORY", cfg["wikimedia"]["repository_url"].replace("https://github.com/", "")
    )
    configured_contact = str(cfg["wikimedia"].get("contact_identifier") or "").strip()
    user_agent = cfg["wikimedia"]["user_agent_template"].format(
        repository_url=repo_url,
        contact_identifier=configured_contact,
    )

    client = WikimediaClient(
        user_agent=user_agent,
        delay_seconds=args.delay_seconds,
        metadata_batch_size=int(cfg["wikimedia"].get("metadata_batch_size", 10)),
        max_retries=int(cfg["wikimedia"]["max_retries"]),
        consecutive_429_stop=int(cfg["wikimedia"]["consecutive_429_stop"]),
    )
    ensure_model(Path(paths["yunet_model"]), cfg["yunet"]["model_url"])
    classifier = YuNetClassifier(
        model_path=Path(paths["yunet_model"]),
        min_confidence=float(cfg["yunet"]["min_confidence"]),
        min_face_area_fraction=float(cfg["yunet"]["min_face_area_fraction"]),
        similar_face_area_ratio=float(cfg["yunet"]["similar_face_area_ratio"]),
    )

    hash_first: Dict[str, str] = {}
    for r in download_rows:
        if r.get("download_status") == "downloaded" and r.get("sha256") and not r.get("duplicate_status"):
            hash_first.setdefault(str(r["sha256"]), str(r["candidate_id"]))

    release_tag = cfg["github"]["release_tag"]
    terminal_since_durable = 0
    dirty_ranges = set()
    rate_limit_stop = False
    metadata_cache: Dict[str, Dict[str, Any]] = {}

    def package_range_for_index(idx: int) -> Tuple[int, int]:
        current_1 = idx + 1
        start_1 = ((current_1 - 1) // args.package_size) * args.package_size + 1
        return start_1, min(start_1 + args.package_size - 1, len(df))

    def maybe_release_completed_range(idx: int) -> None:
        if args.mode != "full":
            return
        pkg_start, pkg_end = package_range_for_index(idx)
        if not range_is_complete(class_rows, pkg_start, pkg_end):
            return

        range_rows = [r for r in class_rows if pkg_start <= int(r["_row_number"]) <= pkg_end]
        already_asset = next((str(r.get("package_asset")) for r in range_rows if r.get("package_asset")), "")
        all_released = all(str(r.get("package_released", "")).lower() in {"true", "1", "yes"} for r in range_rows)
        if all_released and pkg_start not in dirty_ranges:
            return

        # If retrying a failed row in a previously released range, restore prior accepted
        # image members so the clobbered package remains complete.
        if already_asset:
            restore_release_package_images(
                already_asset,
                release_tag,
                package_dir,
                organized_root.parent,
            )

        pkg = make_package(pkg_start, pkg_end, class_rows, download_rows, organized_root, package_dir)
        if not pkg:
            return
        uploaded = upload_release_assets(
            [
                pkg,
                output_dir / "download_manifest.csv",
                output_dir / "classification_manifest.csv",
                output_dir / "regional_summary.csv",
                output_dir / "final_summary.json",
            ],
            release_tag,
        )
        if uploaded:
            mark_package_released(download_rows, class_rows, pkg_start, pkg_end, pkg.name)
            persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)
            prune_released_range(download_rows, class_rows, pkg_start, pkg_end)
            dirty_ranges.discard(pkg_start)

    def terminal_checkpoint(idx: int, changed: bool) -> None:
        nonlocal terminal_since_durable
        if changed and args.mode == "full":
            pkg_start, _ = package_range_for_index(idx)
            dirty_ranges.add(pkg_start)
        maybe_release_completed_range(idx)
        terminal_since_durable += 1
        if terminal_since_durable >= max(1, args.batch_size):
            persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)
            durable_checkpoint(output_dir, download_dir, organized_root, package_dir, release_tag)
            terminal_since_durable = 0

    try:
        for pos, idx in enumerate(target_indices):
            if STOP_REQUESTED[0]:
                break

            row = d_by_id[str(df.iloc[idx]["candidate_id"])]
            crow = c_by_id[str(row["candidate_id"])]
            cid = str(row["candidate_id"])

            if download_is_durably_reusable(row) and class_is_reusable(crow):
                row["resume_reused"] = True
                crow["resume_reused"] = True
                terminal_checkpoint(idx, changed=False)
                continue

            if row.get("download_status") == "download_failed" and not args.retry_failed:
                # Prior download failures remain failures unless explicitly retried.
                terminal_checkpoint(idx, changed=False)
                continue

            filename = derive_commons_filename(row)
            if cid not in metadata_cache:
                pending: List[Tuple[str, str]] = []
                for ahead_idx in target_indices[pos : pos + int(cfg["wikimedia"].get("metadata_batch_size", 10))]:
                    ahead_row = d_by_id[str(df.iloc[ahead_idx]["candidate_id"])]
                    ahead_crow = c_by_id[str(ahead_row["candidate_id"])]
                    ahead_cid = str(ahead_row["candidate_id"])
                    if ahead_cid in metadata_cache:
                        continue
                    if download_is_durably_reusable(ahead_row) and class_is_reusable(ahead_crow):
                        continue
                    if ahead_row.get("download_status") == "download_failed" and not args.retry_failed:
                        continue
                    pending.append((ahead_cid, derive_commons_filename(ahead_row)))
                batch_results = client.resolve_metadata_batch(
                    [fn for _, fn in pending],
                    int(cfg["wikimedia"]["thumbnail_width"]),
                )
                for pending_cid, pending_filename in pending:
                    metadata_cache[pending_cid] = batch_results.get(
                        pending_filename,
                        {
                            "metadata_status": "parse_error",
                            "error_message": "No metadata result returned for requested Commons filename",
                        },
                    )
            meta = metadata_cache.pop(cid, {
                "metadata_status": "parse_error",
                "error_message": "Metadata cache miss",
            })
            for k, v in meta.items():
                if k in download_fields:
                    row[k] = v

            if meta.get("metadata_status") != "resolved":
                row["download_status"] = "download_failed"
                row["http_status"] = meta.get("metadata_http_status", "")
                row["retry_count"] = meta.get("metadata_retry_count", 0)
                row["error_message"] = meta.get("error_message", "Commons metadata resolution failed")
                crow["classification_status"] = "download_failed"
                persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)
                terminal_checkpoint(idx, changed=True)
                continue

            result = client.download_and_validate(meta.get("resolved_thumbnail_url", ""), download_dir, cid)
            row.update({k: v for k, v in result.items() if k in download_fields})

            if row["download_status"] == "download_failed":
                crow["classification_status"] = "download_failed"
                persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)
                terminal_checkpoint(idx, changed=True)
                continue

            if row["download_status"] == "rejected_decode":
                crow["classification_status"] = "rejected_decode"
                crow["classification_timestamp"] = utc_now()
                persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)
                terminal_checkpoint(idx, changed=True)
                continue

            digest = str(row["sha256"])
            if digest in hash_first and hash_first[digest] != cid:
                first_id = hash_first[digest]
                row["duplicate_status"] = "duplicate_file"
                row["duplicate_of_hash"] = digest
                row["duplicate_of_candidate_id"] = first_id
                crow["classification_status"] = "duplicate_file"
                crow["duplicate_of_candidate_id"] = first_id
                crow["reused_classification_candidate_id"] = first_id
                crow["classification_timestamp"] = utc_now()
                try:
                    Path(str(row["local_filename"])).unlink(missing_ok=True)
                except OSError:
                    pass
                # A duplicate record preserves metadata/hash, but does not retain repeated bytes.
                row["local_filename"] = d_by_id[first_id].get("local_filename", "")
            else:
                hash_first.setdefault(digest, cid)
                classification = classifier.classify(Path(str(row["local_filename"])))
                crow.update({k: v for k, v in classification.items() if k in class_fields})
                crow["classification_timestamp"] = utc_now()
                if crow["classification_status"] in {"accepted", "manual_review"}:
                    organized = organize_image(crow | row, Path(str(row["local_filename"])), organized_root)
                    crow["organized_filename"] = str(organized or "")

            # Required atomic manifest checkpoint after every successfully verified image.
            persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)
            terminal_checkpoint(idx, changed=True)

        if args.mode == "test" and not STOP_REQUESTED[0]:
            merged_test = []
            test_complete = True
            for idx in target_indices:
                cid = str(df.iloc[idx]["candidate_id"])
                merged = c_by_id[cid] | d_by_id[cid]
                merged_test.append(merged)
                if c_by_id[cid].get("classification_status") not in TERMINAL_CLASS_STATUSES:
                    test_complete = False
            for cat in ["front", "three_quarter", "side", "manual_review"]:
                write_contact_sheet(merged_test, cat, contact_dir / f"test_{cat}.jpg")
            if test_complete:
                atomic_write_json(
                    {
                        "completed": True,
                        "candidate_scope": 50,
                        "completed_at": utc_now(),
                        "input_candidate_records": 4212,
                    },
                    output_dir / "test_gate.json",
                )
            else:
                raise RuntimeError("The test did not finish all 50 selected candidate records.")

        if args.mode == "full":
            # Final pass only releases fully terminal ranges. Partial ranges remain in checkpoint_state.zip.
            for pkg_start in range(1, len(df) + 1, args.package_size):
                pkg_end = min(pkg_start + args.package_size - 1, len(df))
                if range_is_complete(class_rows, pkg_start, pkg_end):
                    maybe_release_completed_range(pkg_start - 1)

    except StopForRateLimit as exc:
        rate_limit_stop = True
        print(f"[rate-limit] {exc}", file=sys.stderr, flush=True)
    finally:
        summary = persist_all(download_rows, class_rows, download_fields, class_fields, df, output_dir, args.mode, scope_count)
        summary["http_image_requests_this_run"] = client.http_image_requests
        summary["stopped_for_rate_limit"] = rate_limit_stop
        summary["stopped_for_signal"] = STOP_REQUESTED[0]
        atomic_write_json(summary, output_dir / "final_summary.json")

        durable_checkpoint(output_dir, download_dir, organized_root, package_dir, release_tag)
        upload_release_assets(
            [*contact_dir.glob("test_*.jpg"), output_dir / "test_gate.json"],
            release_tag,
        )
        print(json.dumps(summary, indent=2), flush=True)

    if STOP_REQUESTED[0]:
        return 2
    if rate_limit_stop:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
