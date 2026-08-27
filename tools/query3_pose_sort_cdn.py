from __future__ import annotations

import csv
import hashlib
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import mediapipe as mp

import query3_pose_sort as base

OUT = base.OUT


def cdn_urls(filename: str):
    name = unicodedata.normalize("NFC", filename.replace(" ", "_"))
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    enc = quote(name, safe="")
    root = f"https://upload.wikimedia.org/wikipedia/commons/{digest[0]}/{digest[:2]}/{enc}"
    thumb = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{digest[0]}/{digest[:2]}/{enc}/1800px-{enc}"
    return thumb, root


def fetch_one(i, qid, m):
    label = m.get("label", qid)
    filename = m.get("commons_filename")
    stem = f"{i:04d}_{base.safe_slug(label)}_{qid}"
    if not filename:
        return qid, label, filename, None, "", "no P18 image on Wikidata"

    suffix = Path(filename).suffix.lower()
    thumb_url, original_url = cdn_urls(filename)
    # Direct thumb paths are predictable for JPEG/PNG. For TIFF/PDF and for
    # images smaller than 1800 px, fall back to the original CDN object.
    urls = [thumb_url, original_url] if suffix in {".jpg", ".jpeg", ".png"} else [original_url]
    last = None
    for url in urls:
        for attempt in range(3):
            try:
                r = base.SESSION.get(url, timeout=35, allow_redirects=True)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    pause = float(retry_after) if retry_after and retry_after.isdigit() else 3.0 * (attempt + 1)
                    time.sleep(min(pause, 15.0))
                    continue
                if r.status_code in {403, 404}:
                    last = RuntimeError(f"HTTP {r.status_code}")
                    break
                r.raise_for_status()
                ctype = r.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if not ctype.startswith("image/"):
                    raise RuntimeError(f"not an image: {ctype}")
                ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/tiff": ".tif"}.get(ctype, ".jpg")
                path = OUT / "_downloads" / f"{stem}{ext}"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(r.content)
                return qid, label, filename, path, url, ""
            except Exception as e:
                last = e
                time.sleep(1.5 * (attempt + 1))
    return qid, label, filename, None, original_url, str(last)[:500]


def main():
    meta = base.entity_metadata(base.QIDS)
    fetched = {}
    # Keep concurrency modest to be polite to Wikimedia's upload CDN.
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_one, i, qid, meta.get(qid, {})): (i, qid) for i, qid in enumerate(base.QIDS, 1)}
        done = 0
        for fut in as_completed(futs):
            _, qid = futs[fut]
            fetched[qid] = fut.result()
            done += 1
            if done % 25 == 0 or done == len(futs):
                ok = sum(1 for v in fetched.values() if v[3] is not None)
                print(f"downloaded/attempted {done}/{len(futs)}; ok={ok}", flush=True)

    rows = []
    with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=5, refine_landmarks=False, min_detection_confidence=0.30) as mesh:
        for i, qid in enumerate(base.QIDS, 1):
            _, label, filename, path, source_url, fetch_error = fetched[qid]
            category = "uncertain"
            yaw = yaw_pnp = None
            face_count = 0
            note = ""
            status = "ok"
            error = fetch_error
            local_path = path
            if path is None:
                status = "error"
            else:
                try:
                    rgb = base.load_rgb(path)
                    category, yaw, yaw_pnp, face_count, note = base.estimate_pose(rgb, mesh)
                    final_path = OUT / category / path.name
                    path.replace(final_path)
                    local_path = final_path
                except Exception as e:
                    status = "error"
                    error = str(e)[:500]
                    final_path = OUT / "uncertain" / path.name
                    path.replace(final_path)
                    local_path = final_path
            rows.append({
                "qid": qid,
                "personLabel": label,
                "commons_filename": filename or "",
                "category": category,
                "estimated_yaw_deg": "" if yaw is None else f"{yaw:.2f}",
                "pnp_yaw_deg": "" if yaw_pnp is None else f"{yaw_pnp:.2f}",
                "faces_detected": face_count,
                "status": status,
                "note": note,
                "error": error,
                "source_url": source_url,
                "output_file": "" if local_path is None else str(local_path.relative_to(OUT)),
            })
            if i % 25 == 0 or i == len(base.QIDS):
                print(f"classified {i}/{len(base.QIDS)}", flush=True)

    dl = OUT / "_downloads"
    if dl.exists():
        for p in dl.iterdir():
            try: p.unlink()
            except OSError: pass
        try: dl.rmdir()
        except OSError: pass

    with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    counts = {k: sum(r["category"] == k for r in rows) for k in ("front", "three_quarter", "side", "uncertain")}
    errors = sum(r["status"] != "ok" for r in rows)
    (OUT / "README.txt").write_text(
        "Query-3 Wikimedia images sorted by estimated head pose.\n"
        f"Unique people: {len(base.QIDS)}\n"
        + "\n".join(f"{k}: {v}" for k, v in counts.items())
        + f"\nDownload/classification errors: {errors}\n\n"
        "Files are fetched from Wikimedia's upload CDN; JPEG/PNG images use an 1800 px derivative when available.\n"
        "Pose bins: front <15 degrees, three-quarter 15-50 degrees, side >=50 degrees.\n"
        "Near-threshold or undetected faces are placed in uncertain.\n"
        "For multi-person photos, the largest detected face is treated as the subject.\n"
        "See manifest.csv for sources, yaw estimates, and classifications.\n",
        encoding="utf-8",
    )
    print("COUNTS", counts, "errors", errors, flush=True)


if __name__ == "__main__":
    main()
