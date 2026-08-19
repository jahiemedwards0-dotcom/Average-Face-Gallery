#!/usr/bin/env python3
"""Build a 50-person photo ZIP from cited public-figure sources.

Every downloaded candidate is decoded and passed through the repository's strict YuNet
face detector. Zero-face candidates are discarded. The script keeps trying alternate
page/Commons/Wikipedia image candidates for the same roster entry until one passes.
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
import unicodedata
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

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
USER_AGENT = "Mozilla/5.0 (compatible; FaceValidationBot/1.0; +https://github.com/)"


def request(url: str, *, accept: str, timeout: int = 25, max_bytes: int = 25_000_000):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError("response exceeded size limit")
        return data, (resp.headers.get("Content-Type") or "").split(";", 1)[0].lower(), resp.geturl()


def request_text(url: str) -> tuple[str, str]:
    data, _, final = request(url, accept="text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8", max_bytes=8_000_000)
    return data.decode("utf-8", errors="replace"), final


def slug_name(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "_", norm).strip("_") or "person"


def clean_url(value: str) -> str:
    value = html_lib.unescape(value)
    value = value.replace("\\/", "/")
    value = re.sub(r"\\u002[fF]", "/", value)
    value = re.sub(r"\\u003[aA]", ":", value)
    value = value.replace("\\u0026", "&")
    return value.strip("'\" ,)")


def direct_commons_url(source_url: str) -> str | None:
    parsed = urllib.parse.urlparse(source_url)
    marker = "/wiki/File:"
    if "commons.wikimedia.org" not in parsed.netloc or marker not in parsed.path:
        return None
    title = urllib.parse.unquote(parsed.path.split(marker, 1)[1])
    return "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + urllib.parse.quote(title, safe="()_',-.~")


def extract_attr(tag: str, attr: str) -> str | None:
    m = re.search(rf"\b{re.escape(attr)}\s*=\s*['\"]([^'\"]+)['\"]", tag, flags=re.I)
    return clean_url(m.group(1)) if m else None


def extract_page_candidates(page_url: str, text: str, person_name: str) -> list[str]:
    weighted: list[tuple[int, str]] = []
    tokens = [t.lower() for t in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", person_name) if len(t) >= 4]

    for pattern in (
        r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::url)?|twitter:image(?::src)?)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image(?::url)?|twitter:image(?::src)?)["\']',
        r'"(?:headshot|headshotUrl|playerImage|profileImage|photoUrl|imageUrl|imageURL)"\s*:\s*"([^"]+)"',
    ):
        for m in re.finditer(pattern, text, flags=re.I):
            weighted.append((0, clean_url(m.group(1))))

    for m in re.finditer(r"<img\b[^>]*>", text, flags=re.I):
        tag = m.group(0)
        alt = (extract_attr(tag, "alt") or "").lower()
        srcs = []
        for attr in ("src", "data-src", "data-original"):
            u = extract_attr(tag, attr)
            if u:
                srcs.append(u)
        srcset = extract_attr(tag, "srcset")
        if srcset:
            srcs.extend(part.strip().split(" ", 1)[0] for part in srcset.split(",") if part.strip())
        for u in srcs:
            if u.startswith("//"):
                u = "https:" + u
            elif u.startswith("/"):
                u = urllib.parse.urljoin(page_url, u)
            if not u.startswith("http"):
                continue
            score = 1
            if tokens and any(t in alt for t in tokens):
                score = 0
            weighted.append((score, u))

    for m in re.finditer(r"https?:\\?/\\?/images\.volleyballworld\.com[^\"'<>\s]+", text, flags=re.I):
        weighted.append((0, clean_url(m.group(0))))

    for m in re.finditer(r"https?:\\?/\\?/[^\"'<>\s]+", text, flags=re.I):
        u = clean_url(m.group(0))
        low = u.lower().split("?", 1)[0]
        if any(ext in low for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif")) or "/image/upload/" in low:
            weighted.append((2, u))

    def penalty(url: str) -> int:
        low = url.lower()
        return 5 if any(x in low for x in ("logo", "flag", "icon", "sprite", "banner", "advert", "sponsor", "placeholder", "tournament")) else 0

    seen = set()
    out = []
    for score, u in sorted(weighted, key=lambda x: x[0] + penalty(x[1])):
        if not u.startswith("http") or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def commons_search(name: str, limit: int = 12) -> list[str]:
    params = urllib.parse.urlencode({
        "action": "query",
        "generator": "search",
        "gsrsearch": name,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json",
        "origin": "*",
    })
    try:
        text, _ = request_text("https://commons.wikimedia.org/w/api.php?" + params)
        payload = json.loads(text)
    except Exception:
        return []
    out = []
    for page in ((payload.get("query") or {}).get("pages") or {}).values():
        for ii in page.get("imageinfo") or []:
            if (ii.get("mime") or "").startswith("image/") and ii.get("url"):
                out.append(ii["url"])
    return out


def wikipedia_pageimages(name: str, lang: str) -> list[str]:
    params = urllib.parse.urlencode({
        "action": "query",
        "generator": "search",
        "gsrsearch": name,
        "gsrlimit": 5,
        "prop": "pageimages",
        "piprop": "original|thumbnail",
        "pithumbsize": 1600,
        "format": "json",
        "origin": "*",
    })
    try:
        text, _ = request_text(f"https://{lang}.wikipedia.org/w/api.php?" + params)
        payload = json.loads(text)
    except Exception:
        return []
    out = []
    for page in ((payload.get("query") or {}).get("pages") or {}).values():
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
    try:
        text, final_page = request_text(source)
        urls.extend(extract_page_candidates(final_page, text, name))
    except Exception as exc:
        print(f"  source page fetch failed: {type(exc).__name__}: {exc}")
    urls.extend(commons_search(name))
    urls.extend(wikipedia_pageimages(name, "en"))
    urls.extend(wikipedia_pageimages(name, "es"))
    seen = set()
    return [u for u in urls if u and not (u in seen or seen.add(u))]


def extension_for(url: str, content_type: str) -> str:
    mapping = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/bmp": ".bmp", "image/tiff": ".tif"}
    if content_type in mapping:
        return mapping[content_type]
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext if ext in IMAGE_EXTS else ".jpg"


def validate_candidate(url: str, tmp_dir: Path, model_path: Path, used_hashes: set[str]):
    try:
        data, content_type, final_url = request(url, accept="image/avif,image/webp,image/apng,image/*,*/*;q=0.8")
    except Exception as exc:
        return None, f"download-error:{type(exc).__name__}"
    if len(data) < 4_000:
        return None, "too-small"
    digest = hashlib.sha256(data).hexdigest()
    if digest in used_hashes:
        return None, "duplicate-bytes"
    path = tmp_dir / ("candidate" + extension_for(final_url, content_type))
    path.write_bytes(data)
    if read_image(path) is None:
        path.unlink(missing_ok=True)
        return None, "not-decodable-image"
    result = detect_face(path, DEFAULT_SCORE_THRESHOLD, DEFAULT_MIN_FACE_PX, model_path)
    if not result["detected"]:
        path.unlink(missing_ok=True)
        return None, result["detector"]
    return (path, final_url, digest, result), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("dominican_public_figures_complete_50.zip"))
    ap.add_argument("--manifest", type=Path, default=Path("replacement_face_manifest.csv"))
    ap.add_argument("--max-candidates", type=int, default=45)
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
        out_dir = work / "final"
        out_dir.mkdir()

        for row in roster:
            idx = int(row["#"])
            name = row["name"]
            safe = slug_name(name)
            print(f"\n[{idx:02d}/50] {name}")
            urls = candidate_urls(row)
            print(f"  candidates={len(urls)}")
            kept = False
            for n, url in enumerate(urls[: args.max_candidates], 1):
                candidate, err = validate_candidate(url, work, model_path, used_hashes)
                if candidate is None:
                    print(f"    {n:02d} DROP {err}: {url[:160]}")
                    continue
                temp_path, final_url, digest, result = candidate
                dest = out_dir / f"{idx:02d}_{safe}{temp_path.suffix.lower()}"
                shutil.move(str(temp_path), dest)
                used_hashes.add(digest)
                rows_out.append({
                    "index": idx,
                    "name": name,
                    "status": "replacement",
                    "source_page": row["source_url"],
                    "image_url": final_url,
                    "detector": result["detector"],
                    "score": result["score"],
                    "face_count": result["face_count"],
                    "sha256": digest,
                })
                print(f"    {n:02d} PASS {result['detector']} score={result['score']}: {final_url}")
                kept = True
                break
            if not kept:
                rows_out.append({
                    "index": idx,
                    "name": name,
                    "status": "missing",
                    "source_page": row["source_url"],
                    "image_url": "",
                    "detector": "",
                    "score": "",
                    "face_count": 0,
                    "sha256": "",
                })
                print("  MISSING: no candidate passed strict face detection")

        fields = ["index", "name", "status", "source_page", "image_url", "detector", "score", "face_count", "sha256"]
        with args.manifest.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows_out)

        with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out_dir.iterdir()):
                if p.suffix.lower() in IMAGE_EXTS:
                    zf.write(p, p.name)
            zf.write(args.manifest, args.manifest.name)
            zf.write(args.roster, "roster.csv")

    passed = sum(r["status"] != "missing" for r in rows_out)
    missing = 50 - passed
    print(f"\nRESULT total={passed}/50 missing={missing} output={args.output}")
    return 0 if passed == 50 else 2


if __name__ == "__main__":
    raise SystemExit(main())
