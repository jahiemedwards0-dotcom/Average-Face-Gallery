from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from PIL import Image, ImageDraw, ImageFont


def slug(value: Any) -> str:
    text = str(value or "unknown").strip()
    if not text or text.lower() == "nan":
        text = "unknown"
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:120] or "unknown"


def accepted_destination(row: Dict[str, Any], root: Path) -> Path:
    gender = slug(row.get("gender_label") or "unknown")
    return root / "accepted" / slug(row.get("view")) / slug(row.get("country")) / slug(row.get("region")) / gender


def manual_destination(row: Dict[str, Any], root: Path) -> Path:
    return root / "manual_review" / slug(row.get("country")) / slug(row.get("region"))


def organize_image(row: Dict[str, Any], source: Path, organized_root: Path) -> Optional[Path]:
    status = row.get("classification_status")
    if status == "accepted":
        dest_dir = accepted_destination(row, organized_root)
    elif status == "manual_review":
        dest_dir = manual_destination(row, organized_root)
    else:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name
    if not dest.exists():
        try:
            os.link(source, dest)
        except OSError:
            shutil.copy2(source, dest)
    return dest


def write_contact_sheet(
    rows: List[Dict[str, Any]],
    category: str,
    output_path: Path,
    cell_w: int = 220,
    cell_h: int = 270,
    columns: int = 4,
) -> None:
    selected = [r for r in rows if (r.get("view") == category and r.get("classification_status") == "accepted")]
    if category == "manual_review":
        selected = [r for r in rows if r.get("classification_status") == "manual_review"]
    if not selected:
        return
    rows_n = (len(selected) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows_n * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, row in enumerate(selected):
        path = Path(str(row.get("local_filename") or ""))
        if not path.exists():
            continue
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((cell_w - 12, cell_h - 58))
        except Exception:
            continue
        x = (i % columns) * cell_w + 6
        y = (i // columns) * cell_h + 6
        canvas.paste(img, (x + (cell_w - 12 - img.width) // 2, y))
        label = f"{row.get('candidate_id','')} | {row.get('region','')}\nyaw={row.get('estimated_yaw','')} | {row.get('confidence','')}"
        draw.multiline_text((x, y + cell_h - 48), label[:120], fill="black", font=font, spacing=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=90)


def make_package(
    start_1based: int,
    end_1based: int,
    rows: List[Dict[str, Any]],
    download_rows: List[Dict[str, Any]],
    organized_root: Path,
    output_dir: Path,
) -> Optional[Path]:
    package = output_dir / f"harvest_{start_1based:04d}_{end_1based:04d}.zip"
    eligible = [
        r for r in rows
        if start_1based <= int(r.get("_row_number", 0)) <= end_1based
    ]
    dlookup = {str(r.get("candidate_id")): r for r in download_rows}
    if not eligible:
        return None

    package.parent.mkdir(parents=True, exist_ok=True)
    tmp = package.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for row in eligible:
            status = row.get("classification_status")
            if status not in {"accepted", "manual_review"}:
                continue
            local = Path(str(row.get("organized_filename") or ""))
            if local.exists():
                arc = local.relative_to(organized_root.parent)
                z.write(local, str(arc))
        # Include manifests limited to this package range.
        c_fields = sorted({k for r in eligible for k in r.keys() if not k.startswith("_")})
        c_buf = []
        import io
        sio = io.StringIO()
        writer = csv.DictWriter(sio, fieldnames=c_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(eligible)
        z.writestr("classification_manifest.csv", sio.getvalue())

        drows = [dlookup[str(r.get("candidate_id"))] for r in eligible if str(r.get("candidate_id")) in dlookup]
        if drows:
            d_fields = sorted({k for r in drows for k in r.keys() if not k.startswith("_")})
            sio = io.StringIO()
            writer = csv.DictWriter(sio, fieldnames=d_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(drows)
            z.writestr("download_manifest.csv", sio.getvalue())

        attribution_lines = ["Wikimedia Commons attribution metadata\n"]
        for r in drows:
            if r.get("download_status") != "downloaded":
                continue
            attribution_lines.append(
                f"{r.get('candidate_id')}\t{r.get('commons_file_page_url','')}\t"
                f"{r.get('license_name','')}\t{r.get('license_url','')}\t"
                f"{r.get('artist','')}\t{r.get('credit','')}\t{r.get('attribution','')}"
            )
        z.writestr("ATTRIBUTION.tsv", "\n".join(attribution_lines) + "\n")
    os.replace(tmp, package)
    return package


def _run_gh(args: List[str]) -> bool:
    try:
        subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return True
    except Exception as exc:
        print(f"[release] gh command failed: {exc}", flush=True)
        return False


def ensure_release(tag: str) -> bool:
    if not os.environ.get("GH_TOKEN") or not os.environ.get("GITHUB_REPOSITORY"):
        return False
    if _run_gh(["release", "view", tag, "--repo", os.environ["GITHUB_REPOSITORY"]]):
        return True
    return _run_gh([
        "release", "create", tag,
        "--repo", os.environ["GITHUB_REPOSITORY"],
        "--title", "Wikimedia Commons harvest checkpoint",
        "--notes", "Durable checkpoint and sequential harvest packages. Manifests distinguish candidates from verified downloads.",
        "--prerelease",
    ])


def upload_release_assets(paths: Iterable[Path], tag: str) -> bool:
    paths = [p for p in paths if p and p.exists()]
    if not paths or not ensure_release(tag):
        return False
    args = ["release", "upload", tag, "--repo", os.environ["GITHUB_REPOSITORY"], "--clobber", *map(str, paths)]
    return _run_gh(args)



def restore_release_package_images(asset_name: str, tag: str, package_dir: Path, organized_parent: Path) -> bool:
    """Restore only organized image members from an existing Release package."""
    if not os.environ.get("GH_TOKEN") or not os.environ.get("GITHUB_REPOSITORY"):
        return False
    package_dir.mkdir(parents=True, exist_ok=True)
    local = package_dir / asset_name
    if not local.exists():
        ok = _run_gh([
            "release", "download", tag,
            "--repo", os.environ["GITHUB_REPOSITORY"],
            "--pattern", asset_name,
            "--dir", str(package_dir),
        ])
        if not ok or not local.exists():
            return False
    try:
        with zipfile.ZipFile(local, "r") as z:
            for member in z.infolist():
                if member.filename.startswith("organized/") and not member.is_dir():
                    z.extract(member, path=organized_parent)
        return True
    except Exception as exc:
        print(f"[release] failed to restore package images from {asset_name}: {exc}", flush=True)
        return False


def make_checkpoint_zip(paths: Iterable[Path], output_path: Path, base_dir: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in paths:
            if not path.exists():
                continue
            if path.is_file():
                z.write(path, str(path.relative_to(base_dir)))
            else:
                for child in path.rglob("*"):
                    if child.is_file():
                        z.write(child, str(child.relative_to(base_dir)))
    os.replace(tmp, output_path)
    return output_path
