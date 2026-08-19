#!/usr/bin/env python3
"""Patch only missing/incorrect roster slots in the generated public-figure ZIP.

Identity safety:
- Volleyball targets come from one exact Volleyball World player-ID page.
- Only the player-portrait Cloudinary rendition pattern is considered.
- Rosa Santana uses one manually verified exact-name press photo.
- Every candidate still must pass the strict YuNet detector.
"""

from __future__ import annotations

import csv
import hashlib
import html as html_lib
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from filter_faces import (
    DEFAULT_MIN_FACE_PX,
    DEFAULT_SCORE_THRESHOLD,
    detect_face,
    ensure_yunet_model,
    read_image,
)

USER_AGENT = "Mozilla/5.0 (compatible; FaceValidationBot/1.0; +https://github.com/)"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Slots 16/32/35/42/43 were face-detectable but identity-unsafe in the first refill.
# Slots 36-41 and 44-50 were missing.
TARGETS = {
    16: {
        "name": "Rosa Angelica Santana",
        "page": "https://hoy.com.do/rosa-angelica-con-gran-actuacion-en-eventos/",
        "direct": ["https://hoy.com.do/wp-content/uploads/2022/09/Rosa-Angelica-Ramirez-Santana_-01.jpg"],
    },
    32: {"name": "Natalia Martinez", "page": "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/players/139923"},
    35: {"name": "Iliana Rodriguez Fung", "page": "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/players/182751"},
    36: {"name": "Yanlis Feliz Sena", "page": "https://es.volleyballworld.com/volleyball/competitions/club-world-championship-women/players/157914"},
    37: {"name": "Ailyn Liberato", "page": "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/players/173526"},
    38: {"name": "Selanny Puente Estrella", "page": "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/players/183310"},
    39: {"name": "Esthefany Rabit", "page": "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/2022/players/168727"},
    40: {"name": "Ana Patricia Encarnacion Montero", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/206369"},
    41: {"name": "Thais Chantal Cocly Vasquez", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/191765"},
    42: {"name": "Estel Santos Mateo", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/206587"},
    43: {"name": "Aurelina Ruiz Rosario", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/213373"},
    44: {"name": "Julie Millaray Arias Alejo", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/191753"},
    45: {"name": "Valerie Mariel Vargas Guzman", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/213380"},
    46: {"name": "Harleny Linette De los Santos Baez", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/223204"},
    47: {"name": "Jakarlis Marianni Lima Garcia", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/213386"},
    48: {"name": "Glorybell Puente Estrella", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/191891"},
    49: {"name": "Jismeily Flete Savinon", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u21-world-championship/players/191755"},
    50: {"name": "Dilenny Michel Maleno Mendez", "page": "https://en.volleyballworld.com/volleyball/competitions/women-u19-world-championship/2023/players/191771"},
}


def fetch(url: str, accept: str, max_bytes: int = 25_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept, "Accept-Language": "en-US,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError("response too large")
        return data, (resp.headers.get("Content-Type") or "").split(";", 1)[0].lower(), resp.geturl()


def clean_url(value: str) -> str:
    value = html_lib.unescape(value).replace("\\/", "/")
    value = re.sub(r"\\u002[fF]", "/", value)
    value = re.sub(r"\\u003[aA]", ":", value)
    value = value.replace("\\u0026", "&")
    return value.strip("'\" ,)")


def page_portraits(page_url: str) -> list[str]:
    data, _, _ = fetch(page_url, "text/html,application/xhtml+xml,*/*;q=0.8", 8_000_000)
    text = data.decode("utf-8", errors="replace")
    found = []
    for m in re.finditer(r"https?:\\?/\\?/images\.volleyballworld\.com[^\"'<>\s]+", text, flags=re.I):
        u = clean_url(m.group(0))
        low = u.lower()
        if "/fivb-prd/" in low and "t_editorial_squared_6_desktop" in low:
            found.append(u)
    # Also catch URLs escaped without the scheme slash pattern in JSON blobs.
    for m in re.finditer(r"https://images\.volleyballworld\.com[^\"'<>\s]+", text, flags=re.I):
        u = clean_url(m.group(0))
        low = u.lower()
        if "/fivb-prd/" in low and "t_editorial_squared_6_desktop" in low:
            found.append(u)
    seen = set()
    return [u for u in found if not (u in seen or seen.add(u))]


def ext_for(url: str, content_type: str) -> str:
    mapping = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/bmp": ".bmp", "image/tiff": ".tif"}
    if content_type in mapping:
        return mapping[content_type]
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext if ext in IMAGE_EXTS else ".jpg"


def validate(url: str, work: Path, model: Path, used_hashes: set[str]):
    try:
        data, ctype, final_url = fetch(url, "image/avif,image/webp,image/apng,image/*,*/*;q=0.8")
    except Exception as exc:
        return None, f"download-error:{type(exc).__name__}"
    digest = hashlib.sha256(data).hexdigest()
    if digest in used_hashes:
        return None, "duplicate-bytes"
    p = work / ("candidate" + ext_for(final_url, ctype))
    p.write_bytes(data)
    if read_image(p) is None:
        p.unlink(missing_ok=True)
        return None, "not-decodable"
    result = detect_face(p, DEFAULT_SCORE_THRESHOLD, DEFAULT_MIN_FACE_PX, model)
    if not result["detected"]:
        p.unlink(missing_ok=True)
        return None, result["detector"]
    return (p, final_url, digest, result), None


def index_from_name(name: str) -> int | None:
    m = re.match(r"^(\d{2})_", Path(name).name)
    return int(m.group(1)) if m else None


def main() -> int:
    baseline_zip = Path("generated/dominican_public_figures_complete_50.zip")
    baseline_manifest = Path("generated/replacement_face_manifest.csv")
    output_zip = Path("dominican_public_figures_complete_50.zip")
    output_manifest = Path("replacement_face_manifest.csv")
    if not baseline_zip.exists() or not baseline_manifest.exists():
        raise RuntimeError("baseline generated ZIP/manifest is missing")

    model = ensure_yunet_model()
    rows = list(csv.DictReader(baseline_manifest.open(encoding="utf-8")))
    by_index = {int(r["index"]): r for r in rows}
    used_hashes = {r["sha256"] for r in rows if r.get("sha256") and int(r["index"]) not in TARGETS}

    with tempfile.TemporaryDirectory(prefix="patch_faces_") as td:
        work = Path(td)
        out_dir = work / "images"
        out_dir.mkdir()
        with zipfile.ZipFile(baseline_zip) as zf:
            for info in zf.infolist():
                if Path(info.filename).suffix.lower() not in IMAGE_EXTS:
                    continue
                idx = index_from_name(info.filename)
                if idx in TARGETS:
                    continue
                target = out_dir / Path(info.filename).name
                target.write_bytes(zf.read(info))

        for idx, spec in TARGETS.items():
            print(f"\n[{idx}/50] {spec['name']}")
            urls = list(spec.get("direct", []))
            if "volleyballworld.com" in spec["page"]:
                try:
                    portraits = page_portraits(spec["page"])
                    print(f"  player portraits found={len(portraits)}")
                    urls.extend(portraits)
                except Exception as exc:
                    print(f"  page-error:{type(exc).__name__}:{exc}")
            seen = set()
            urls = [u for u in urls if not (u in seen or seen.add(u))]
            passed = None
            for n, url in enumerate(urls, 1):
                candidate, err = validate(url, work, model, used_hashes)
                if candidate is None:
                    print(f"  {n:02d} DROP {err}: {url[:160]}")
                    continue
                passed = candidate
                break
            if passed is None:
                print("  MISSING identity-safe face")
                by_index[idx] = {
                    "index": str(idx), "name": spec["name"], "status": "missing",
                    "source_page": spec["page"], "image_url": "", "detector": "",
                    "score": "", "face_count": "0", "sha256": "",
                }
                continue
            p, final_url, digest, result = passed
            safe = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", spec["name"]).encode("ascii", "ignore").decode()).strip("_")
            dest = out_dir / f"{idx:02d}_{safe}{p.suffix.lower()}"
            shutil.move(str(p), dest)
            used_hashes.add(digest)
            by_index[idx] = {
                "index": str(idx), "name": spec["name"], "status": "replacement",
                "source_page": spec["page"], "image_url": final_url,
                "detector": result["detector"], "score": str(result["score"]),
                "face_count": str(result["face_count"]), "sha256": digest,
            }
            print(f"  PASS {result['detector']} score={result['score']}: {final_url}")

        fields = ["index", "name", "status", "source_page", "image_url", "detector", "score", "face_count", "sha256"]
        final_rows = [by_index[i] for i in range(1, 51)]
        with output_manifest.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(final_rows)

        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out_dir.iterdir()):
                zf.write(p, p.name)
            zf.write(output_manifest, output_manifest.name)
            zf.write("data/dominican_public_figures_manifest.csv", "roster.csv")

    missing = [r for r in final_rows if r["status"] == "missing"]
    print(f"\nRESULT images={50-len(missing)}/50 missing={len(missing)}")
    for r in missing:
        print(f"MISSING {r['index']} {r['name']}")
    return 0 if not missing else 2


if __name__ == "__main__":
    import unicodedata
    raise SystemExit(main())
