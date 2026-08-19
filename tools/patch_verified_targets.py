#!/usr/bin/env python3
"""Patch the 18 missing/identity-unsafe slots with different qualifying women.

Each replacement is tied to a specific athlete/profile page. The script extracts only
page-associated image candidates and runs the repository's strict YuNet detector on
every candidate. Images with no detected face are discarded. No fuzzy person search is
used in this patch.
"""

from __future__ import annotations

import csv
import hashlib
import html as html_lib
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

USER_AGENT = "Mozilla/5.0 (compatible; FaceValidationBot/1.0; +https://github.com/)"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".avif"}

# All 18 are Dominican Republic senior/youth national-team players or Dominican-born
# college players. Their profile pages are exact-name sources rather than search results.
TARGETS = {
    16: {"name": "Paloma Pena", "page": "https://floridagators.com/sports/womens-soccer/roster/paloma-pea/18212"},
    32: {"name": "Odaliana Gomez", "page": "https://fiusports.com/sports/womens-soccer/roster/odaliana-gomez/13228"},
    35: {"name": "Gabriella Marte", "page": "https://gohofstra.com/sports/womens-soccer/roster/gabriella-marte/15648"},
    36: {"name": "Jazlyn Oviedo", "page": "https://uvmathletics.com/sports/womens-soccer/roster/jazlyn-oviedo/12301"},
    37: {"name": "Kristina Garcia", "page": "https://stonybrookathletics.com/sports/womens-soccer/roster/kristina-garcia/10403"},
    38: {"name": "Stella Tapia", "page": "https://mgoblue.com/sports/womens-soccer/roster/stella-tapia/28349"},
    39: {"name": "Jazmin Jackson", "page": "https://vcuathletics.com/sports/womens-soccer/roster/jazmin-jackson/6385"},
    40: {"name": "Liliane Clase Baez", "page": "https://tsusports.com/sports/womens-soccer/roster/liliane-clase-baez/7148"},
    41: {"name": "Mia Asenjo", "page": "https://ucfknights.com/sports/womens-soccer/roster/player/mia-asenjo"},
    42: {"name": "Angelina Vargas", "page": "https://brownbears.com/sports/womens-soccer/roster/angelina-vargas/23808"},
    43: {"name": "Alexa Pacheco", "page": "https://www.gbcathletics.com/news/2024/2/27/womens-soccer-alexa-pacheco-competes-for-the-dominican-republic-at-the-concacaf-womens-gold-cup.aspx"},
    44: {"name": "Emely Pichardo", "page": "https://bartonbulldogs.com/sports/womens-soccer/roster/emely-pichardo/5606"},
    45: {"name": "Dahien Cabrera", "page": "https://ewutigerpride.com/sports/womens-soccer/roster/dahien-cabrera/3721"},
    46: {"name": "Nadia Colon", "page": "https://goutrgv.com/sports/womens-soccer/roster/nadia-colon/9020"},
    47: {"name": "Renata Mercedes", "page": "https://fordhamsports.com/sports/womens-soccer/roster/renata-mercedes/15790"},
    48: {"name": "Alyse Then", "page": "https://huskers.com/sports/soccer/roster/player/alyse-then"},
    49: {"name": "Jaylen Vallecillo", "page": "https://redstormsports.com/sports/womens-soccer/roster/vallecillo-jaylen/6327"},
    50: {"name": "Alyssa Oviedo", "page": "https://uvmathletics.com/sports/womens-soccer/roster/alyssa-oviedo/6275"},
}


def fetch(url: str, accept: str, max_bytes: int = 25_000_000):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError("response too large")
        return (
            data,
            (resp.headers.get("Content-Type") or "").split(";", 1)[0].lower(),
            resp.geturl(),
        )


def clean_url(value: str, page_url: str) -> str:
    value = html_lib.unescape(value).replace("\\/", "/")
    value = re.sub(r"\\u002[fF]", "/", value)
    value = re.sub(r"\\u003[aA]", ":", value)
    value = value.replace("\\u0026", "&").strip("'\" ,)")
    if value.startswith("//"):
        value = "https:" + value
    elif value.startswith("/"):
        value = urllib.parse.urljoin(page_url, value)
    return value


def attr(tag: str, key: str) -> str | None:
    m = re.search(rf"\b{re.escape(key)}\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
    return html_lib.unescape(m.group(2)) if m else None


def normalized_tokens(name: str) -> list[str]:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    return [t for t in re.findall(r"[a-z0-9]+", ascii_name) if len(t) >= 3]


def name_match(text: str, tokens: list[str]) -> bool:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    hits = sum(t in ascii_text for t in tokens)
    return hits >= min(2, len(tokens)) or (tokens and tokens[-1] in ascii_text)


def page_image_candidates(page_url: str, person_name: str) -> list[str]:
    raw, _, final_page = fetch(page_url, "text/html,application/xhtml+xml,*/*;q=0.8", 10_000_000)
    text = raw.decode("utf-8", errors="replace")
    tokens = normalized_tokens(person_name)
    ranked: list[tuple[int, str, str]] = []

    # 1) Image elements whose alt/title or URL explicitly contains the athlete's name.
    for m in re.finditer(r"<img\b[^>]*>", text, flags=re.I | re.S):
        tag = m.group(0)
        label = " ".join(x for x in (attr(tag, "alt"), attr(tag, "title")) if x)
        urls: list[str] = []
        for key in ("src", "data-src", "data-original", "data-lazy-src"):
            v = attr(tag, key)
            if v:
                urls.append(v)
        for key in ("srcset", "data-srcset"):
            v = attr(tag, key)
            if v:
                urls.extend(part.strip().split()[0] for part in v.split(",") if part.strip())
        for raw_url in urls:
            url = clean_url(raw_url, final_page)
            if not url.startswith("http"):
                continue
            score = 0 if name_match(label, tokens) else 1 if name_match(url, tokens) else 4
            ranked.append((score, url, label))

    # 2) OpenGraph/Twitter image. On an exact-name athlete profile this is normally the
    # player headshot or hero image; keep it behind explicit name-matched <img> tags.
    for pattern in (
        r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::url)?|twitter:image(?::src)?)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image(?::url)?|twitter:image(?::src)?)["\']',
    ):
        for m in re.finditer(pattern, text, flags=re.I | re.S):
            ranked.append((2, clean_url(m.group(1), final_page), "meta-image"))

    # 3) Structured JSON image URLs containing a name token or sitting on this exact profile.
    for m in re.finditer(r'https?:\\?/\\?/[^"\'<>\s]+', text, flags=re.I):
        url = clean_url(m.group(0), final_page)
        low = url.lower().split("?", 1)[0]
        if not (
            any(ext in low for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif"))
            or "/image/upload/" in low
            or "sidearm" in low
        ):
            continue
        score = 1 if name_match(url, tokens) else 3
        ranked.append((score, url, "embedded-url"))

    def penalty(url: str, label: str) -> int:
        low = (url + " " + label).lower()
        bad = (
            "logo", "icon", "sprite", "favicon", "sponsor", "advert", "ticket",
            "conference", "schedule", "placeholder", "footer", "header-logo",
        )
        return 10 if any(x in low for x in bad) else 0

    seen = set()
    out = []
    for score, url, label in sorted(ranked, key=lambda x: x[0] + penalty(x[1], x[2])):
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def ext_for(url: str, content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/avif": ".avif",
        "image/bmp": ".bmp",
        "image/tiff": ".tif",
    }
    if content_type in mapping:
        return mapping[content_type]
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext if ext in IMAGE_EXTS else ".jpg"


def validate(url: str, work: Path, model: Path, used_hashes: set[str]):
    try:
        data, ctype, final_url = fetch(url, "image/avif,image/webp,image/apng,image/*,*/*;q=0.8")
    except Exception as exc:
        return None, f"download-error:{type(exc).__name__}"
    if len(data) < 4_000:
        return None, "too-small"
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
    used_hashes = {
        r["sha256"]
        for r in rows
        if r.get("sha256") and int(r["index"]) not in TARGETS
    }

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
                (out_dir / Path(info.filename).name).write_bytes(zf.read(info))

        for idx, spec in TARGETS.items():
            print(f"\n[{idx}/50] {spec['name']}")
            try:
                urls = page_image_candidates(spec["page"], spec["name"])
            except Exception as exc:
                print(f"  PAGE ERROR {type(exc).__name__}: {exc}")
                urls = []
            print(f"  candidates={len(urls)}")

            passed = None
            for n, url in enumerate(urls[:60], 1):
                candidate, err = validate(url, work, model, used_hashes)
                if candidate is None:
                    print(f"  {n:02d} DROP {err}: {url[:180]}")
                    continue
                passed = candidate
                break

            if passed is None:
                print("  MISSING: no page-associated candidate passed strict face detection")
                by_index[idx] = {
                    "index": str(idx),
                    "name": spec["name"],
                    "status": "missing",
                    "source_page": spec["page"],
                    "image_url": "",
                    "detector": "",
                    "score": "",
                    "face_count": "0",
                    "sha256": "",
                }
                continue

            p, final_url, digest, result = passed
            safe = re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                unicodedata.normalize("NFKD", spec["name"])
                .encode("ascii", "ignore")
                .decode(),
            ).strip("_")
            dest = out_dir / f"{idx:02d}_{safe}{p.suffix.lower()}"
            shutil.move(str(p), dest)
            used_hashes.add(digest)
            by_index[idx] = {
                "index": str(idx),
                "name": spec["name"],
                "status": "replacement",
                "source_page": spec["page"],
                "image_url": final_url,
                "detector": result["detector"],
                "score": str(result["score"]),
                "face_count": str(result["face_count"]),
                "sha256": digest,
            }
            print(f"  PASS {result['detector']} score={result['score']}: {final_url}")

        fields = [
            "index", "name", "status", "source_page", "image_url",
            "detector", "score", "face_count", "sha256",
        ]
        final_rows = [by_index[i] for i in range(1, 51)]
        with output_manifest.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(final_rows)

        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out_dir.iterdir()):
                zf.write(p, p.name)
            zf.write(output_manifest, output_manifest.name)

    missing = [r for r in final_rows if r["status"] == "missing"]
    print(f"\nRESULT images={50-len(missing)}/50 missing={len(missing)}")
    for r in missing:
        print(f"MISSING {r['index']} {r['name']}")
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
