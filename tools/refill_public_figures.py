#!/usr/bin/env python3
"""Refill a 50-person public-figure image set with strict per-image face detection.

The existing 50-image source ZIP is treated as one candidate per roster row. Any row whose
original image has no YuNet-detectable face is replaced by trying image candidates from that
person's cited source page, Wikimedia Commons/Wikipedia APIs, and official-profile image URLs.
A candidate is never kept unless the strict YuNet detector passes it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_lib
import json
import re
import shutil
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from filter_faces import DEFAULT_MIN_FACE_PX, DEFAULT_SCORE_THRESHOLD, detect_face, ensure_yunet_model, read_image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
USER_AGENT = "Mozilla/5.0 (compatible; FaceValidationBot/1.0; +https://github.com/)"


def request_bytes(url: str, timeout: int = 25, max_bytes: int = 25_000_000) -> tuple[bytes, str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = (resp.headers.get("Content-Type") or "").split(";", 1)[0].lower()
        final_url = resp.geturl()
        data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError("candidate exceeded size limit")
        return data, content_type, final_url


def request_text(url: str, timeout: int = 25) -> tuple[str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(8_000_000)
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), resp.geturl()


def slug_name(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "_", norm).strip("_") or "person"


def source_index(path: Path) -> int | None:
    m = re.search(r"_(\d+)(?:\.[^.]+)$", path.name)
    return int(m.group(1)) if m else None


def direct_commons_url(source_url: str) -> str | None:
    parsed = urllib.parse.urlparse(source_url)
    if "commons.wikimedia.org" not in parsed.netloc or "/wiki/File:" not in parsed.path:
        return None
    title = urllib.parse.unquote(parsed.path.split("/wiki/File:", 1)[1])
    return "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + urllib.parse.quote(title, safe="()_',-.~")


def clean_embedded_url(value: str) -> str:
    value = html_lib.unescape(value)
    value = value.replace("\\/", "/")
    value = re.sub(r"\\u002[fF]", "/", value)
    value = re.sub(r"\\u003[aA]", ":", value)
    value = value.replace("\\u0026", "&")
    value = value.strip("'\" ,)")
    return value


def extract_page_candidates(page_url: str, text: str) -> list[str]:
    candidates: list[str] = []

    # Highest priority: social/structured preview images.
    patterns = [
        r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::url)?|twitter:image(?::src)?)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image(?::url)?|twitter:image(?::src)?)["\']',
        r'"(?:image|imageUrl|imageURL|photo|photoUrl|photoURL|headshot|headshotUrl|playerImage|profileImage)"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            candidates.append(clean_embedded_url(m.group(1)))

    # Volleyball World stores player images on this CDN. Prefer them over general page assets.
    for m in re.finditer(r'https?:\\?/\\?/images\.volleyballworld\.com[^"\'<>\s]+', text, flags=re.I):
        candidates.append(clean_embedded_url(m.group(0)))

    # Generic absolute image URLs embedded in HTML/JSON.
    for m in re.finditer(r'https?:\\?/\\?/[^"\'<>\s]+', text, flags=re.I):
        u = clean_embedded_url(m.group(0))
        low = u.lower().split("?", 1)[0]
        if any(ext in low for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif")) or "/image/upload/" in low:
            candidates.append(u)

    # Relative img/src candidates.
    for m in re.finditer(r'(?:src|data-src|data-original)=["\']([^"\']+)["\']', text, flags=re.I):
        u = clean_embedded_url(m.group(1))
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            u = urllib.parse.urljoin(page_url, u)
        if u.startswith("http"):
            candidates.append(u)

    # De-prioritize obvious logos, flags, icons, ads, and competition artwork.
    def rank(u: str) -> tuple[int, int]:
        low = u.lower()
        bad = any(x in low for x in ("logo", "flag", "icon", "sprite", "banner", "advert", "sponsor", "competition", "tournament", "placeholder"))
        playerish = any(x in low for x in ("player", "athlete", "headshot", "profile", "portrait", "fivb-prd", "volleyballworld.com/image/upload"))
        return (0 if playerish else 1, 1 if bad else 0)

    seen = set()
    ordered = []
    for u in sorted(candidates, key=rank):
        if not u.startswith("http") or u in seen:
            continue
        seen.add(u)
        ordered.append(u)
    return ordered


def commons_search_candidates(name: str, limit: int = 8) -> list[str]:
    params = urllib.parse.urlencode({
        "action": "query",
        "generator": "search",
        "gsrsearch": name,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "format": "json",
        "origin": "*",
    })
    url = "https://commons.wikimedia.org/w/api.php?" + params
    try:
        text, _ = request_text(url)
        payload = json.loads(text)
    except Exception:
        return []
    out = []
    pages = (payload.get("query") or {}).get("pages") or {}
    for page in pages.values():
        for ii in page.get("imageinfo") or []:
            mime = (ii.get("mime") or "").lower()
            if mime.startswith("image/") and ii.get("url"):
                out.append(ii["url"])
    return out


def wikipedia_pageimage_candidates(name: str, lang: str = "en") -> list[str]:
    params = urllib.parse.urlencode({
        "action": "query",
        "generator": "search",
        "gsrsearch": name,
        "gsrlimit": 4,
        "prop": "pageimages",
        "piprop": "original|thumbnail",
        "pithumbsize": 1600,
        "format": "json",
        "origin": "*",
    })
    url = f"https://{lang}.wikipedia.org/w/api.php?" + params
    try:
        text, _ = request_text(url)
        payload = json.loads(text)
    except Exception:
        return []
    out = []
    pages = (payload.get("query") or {}).get("pages") or {}
    for page in pages.values():
        if (page.get("original") or {}).get("source"):
            out.append(page["original"]["source"])
        if (page.get("thumbnail") or {}).get("source"):
            out.append(page["thumbnail"]["source"])
    return out


def candidate_urls(row: dict) -> list[str]:
    source = row["source_url"]
    name = row["name"]
    urls: list[str] = []

    direct = direct_commons_url(source)
    if direct:
        urls.append(direct)

    # The cited page itself is authoritative for official-profile images.
    try:
        text, final_page = request_text(source)
        urls.extend(extract_page_candidates(final_page, text))
    except Exception as exc:
        print(f"  page fetch failed: {exc}")

    # Commons/Wikipedia fallbacks are useful for athletes with additional public images.
    urls.extend(commons_search_candidates(name, limit=10))
    urls.extend(wikipedia_pageimage_candidates(name, "en"))
    urls.extend(wikipedia_pageimage_candidates(name, "es"))

    seen = set()
    result = []
    for u in urls:
        if not u or u in seen:
            continue
        seen.add(u)
        result.append(u)
    return result


def choose_extension(url: str, content_type: str) -> str:
    ctype_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tif",
    }
    if content_type in ctype_map:
        return ctype_map[content_type]
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext if ext in IMAGE_EXTS else ".jpg"


def validate_candidate(url: str, tmp_dir: Path, model_path: Path, used_hashes: set[str]):
    try:
        data, content_type, final_url = request_bytes(url)
    except Exception as exc:
        return None, f"download-error:{type(exc).__name__}"
    if len(data) < 4_000:
        return None, "too-small"
    digest = hashlib.sha256(data).hexdigest()
    if digest in used_hashes:
        return None, "duplicate-bytes"

    ext = choose_extension(final_url, content_type)
    temp_path = tmp_dir / ("candidate" + ext)
    temp_path.write_bytes(data)
    if read_image(temp_path) is None:
        temp_path.unlink(missing_ok=True)
        return None, "not-decodable-image"

    result = detect_face(temp_path, DEFAULT_SCORE_THRESHOLD, DEFAULT_MIN_FACE_PX, model_path)
    if not result["detected"]:
        temp_path.unlink(missing_ok=True)
        return None, result["detector"]
    return (temp_path, final_url, digest, result), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", type=Path, required=True)
    ap.add_argument("--source-zip", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("dominican_public_figures_complete_50.zip"))
    ap.add_argument("--manifest", type=Path, default=Path("replacement_face_manifest.csv"))
    ap.add_argument("--max-candidates", type=int, default=35)
    args = ap.parse_args()

    model_path = ensure_yunet_model()
    with args.roster.open(encoding="utf-8-sig", newline="") as f:
        roster = list(csv.DictReader(f))
    if len(roster) != 50:
        raise RuntimeError(f"expected 50 roster rows, got {len(roster)}")

    rows_out = []
    used_hashes: set[str] = set()

    with tempfile.TemporaryDirectory(prefix="refill_faces_") as td:
        work = Path(td)
        src_dir = work / "source"
        out_dir = work / "final"
        src_dir.mkdir()
        out_dir.mkdir()
        with zipfile.ZipFile(args.source_zip) as zf:
            zf.extractall(src_dir)

        originals: dict[int, Path] = {}
        for p in src_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                idx = source_index(p)
                if idx is not None:
                    originals[idx] = p

        for row in roster:
            idx = int(row["#"])
            name = row["name"]
            safe = slug_name(name)
            print(f"\n[{idx:02d}/50] {name}")
            original = originals.get(idx)
            kept = False

            if original is not None:
                result = detect_face(original, DEFAULT_SCORE_THRESHOLD, DEFAULT_MIN_FACE_PX, model_path)
                if result["detected"]:
                    data = original.read_bytes()
                    digest = hashlib.sha256(data).hexdigest()
                    ext = original.suffix.lower() if original.suffix.lower() in IMAGE_EXTS else ".jpg"
                    dest = out_dir / f"{idx:02d}_{safe}{ext}"
                    shutil.copy2(original, dest)
                    used_hashes.add(digest)
                    rows_out.append({
                        "index": idx, "name": name, "status": "kept-original", "source_page": row["source_url"],
                        "image_url": "source-archive", "detector": result["detector"], "score": result["score"],
                        "face_count": result["face_count"], "sha256": digest,
                    })
                    print(f"  PASS original ({result['detector']} score={result['score']})")
                    kept = True
                else:
                    print("  DROP original; searching replacement")

            if kept:
                continue

            urls = candidate_urls(row)
            print(f"  candidates={len(urls)}")
            for n, url in enumerate(urls[: args.max_candidates], 1):
                candidate, err = validate_candidate(url, work, model_path, used_hashes)
                if candidate is None:
                    print(f"    {n:02d} DROP {err}: {url[:140]}")
                    continue
                temp_path, final_url, digest, result = candidate
                ext = temp_path.suffix.lower()
                dest = out_dir / f"{idx:02d}_{safe}{ext}"
                shutil.move(str(temp_path), dest)
                used_hashes.add(digest)
                rows_out.append({
                    "index": idx, "name": name, "status": "replacement", "source_page": row["source_url"],
                    "image_url": final_url, "detector": result["detector"], "score": result["score"],
                    "face_count": result["face_count"], "sha256": digest,
                })
                print(f"    {n:02d} PASS {result['detector']} score={result['score']}: {final_url}")
                kept = True
                break

            if not kept:
                rows_out.append({
                    "index": idx, "name": name, "status": "missing", "source_page": row["source_url"],
                    "image_url": "", "detector": "", "score": "", "face_count": 0, "sha256": "",
                })
                print("  MISSING: no candidate passed strict face detection")

        fields = ["index", "name", "status", "source_page", "image_url", "detector", "score", "face_count", "sha256"]
        with args.manifest.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows_out)

        final_images = sorted(p for p in out_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in final_images:
                zf.write(p, p.name)
            zf.write(args.manifest, args.manifest.name)
            zf.write(args.roster, "roster.csv")

    passed = sum(r["status"] != "missing" for r in rows_out)
    replacements = sum(r["status"] == "replacement" for r in rows_out)
    missing = 50 - passed
    print(f"\nRESULT total={passed}/50 replacements={replacements} missing={missing} output={args.output}")
    return 0 if passed == 50 else 2


if __name__ == "__main__":
    raise SystemExit(main())
