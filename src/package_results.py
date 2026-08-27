from __future__ import annotations

import argparse
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


TERMINAL_DOWNLOAD = {"verified", "verified_duplicate", "download_failed", "rejected_decode"}
TERMINAL_CLASS = {"accepted", "manual_review", "rejected_no_face", "rejected_decode", "duplicate_file", "download_failed"}


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def package_completed_chunks(
    manifest_path: Path,
    output_dir: Path,
    package_dir: Path,
    package_size: int = 250,
) -> list[Path]:
    df = pd.read_csv(manifest_path, keep_default_na=False)
    package_dir.mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    n = len(df)
    for start in range(0, n, package_size):
        end = min(n, start + package_size)
        chunk = df.iloc[start:end].copy()
        # Do not publish partial chunks until every record in that global chunk reached a terminal state.
        if not chunk["classification_status"].isin(TERMINAL_CLASS).all():
            continue
        name = f"harvest_{start+1:04d}_{end:04d}.zip"
        dest = package_dir / name
        if dest.exists():
            made.append(dest)
            continue
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            csv_bytes = chunk.to_csv(index=False).encode("utf-8")
            zf.writestr("manifest.csv", csv_bytes)
            seen_hashes: set[str] = set()
            for _, row in chunk.iterrows():
                digest = str(row.get("sha256") or "")
                source = Path(str(row.get("local_filename") or ""))
                if (str(row.get("duplicate_status") or "") == "duplicate_file" or
                        str(row.get("classification_status") or "") == "duplicate_file"):
                    continue
                if not digest or digest in seen_hashes or not source.exists():
                    continue
                seen_hashes.add(digest)
                organized = str(row.get("organized_filename") or "")
                if organized:
                    org_path = Path(organized)
                    if org_path.is_absolute():
                        try:
                            org_path = org_path.relative_to(Path.cwd())
                        except ValueError:
                            org_path = Path(org_path.name)
                    arc = Path("images") / org_path
                else:
                    arc = Path("images") / source.name
                zf.write(source, arcname=str(arc))
            zf.writestr(
                "package_summary.json",
                json.dumps({
                    "record_start": start + 1,
                    "record_end": end,
                    "records": len(chunk),
                    "verified_records": int(chunk["download_status"].isin(["verified", "verified_duplicate"]).sum()),
                    "unique_hashes": int(chunk.loc[chunk["sha256"] != "", "sha256"].nunique()),
                }, indent=2),
            )
        made.append(dest)
    return made


def make_checkpoint(root: Path, checkpoint_path: Path) -> Path:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    includes = [root / "output", root / "downloads" / "unique", root / "organized"]
    fd, name = tempfile.mkstemp(prefix="checkpoint_", suffix=".zip", dir=checkpoint_path.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as zf:
            for base in includes:
                if not base.exists():
                    continue
                for path in base.rglob("*"):
                    if path.is_file():
                        zf.write(path, arcname=str(path.relative_to(root)))
        os.replace(tmp, checkpoint_path)
    finally:
        tmp.unlink(missing_ok=True)
    return checkpoint_path


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("packages")
    p1.add_argument("--manifest", default="output/classification_manifest.csv")
    p1.add_argument("--output-dir", default="output")
    p1.add_argument("--package-dir", default="packages")
    p1.add_argument("--package-size", type=int, default=250)
    p2 = sub.add_parser("checkpoint")
    p2.add_argument("--root", default=".")
    p2.add_argument("--output", default="packages/checkpoint_state.zip")
    args = ap.parse_args()
    if args.cmd == "packages":
        made = package_completed_chunks(Path(args.manifest), Path(args.output_dir), Path(args.package_dir), args.package_size)
        print(json.dumps({"packages": [str(x) for x in made]}, indent=2))
    else:
        path = make_checkpoint(Path(args.root).resolve(), Path(args.output))
        print(path)


if __name__ == "__main__":
    main()
