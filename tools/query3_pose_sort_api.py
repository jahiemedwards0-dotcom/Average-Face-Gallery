from __future__ import annotations

import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mediapipe as mp
import requests

import query3_pose_sort as base

OUT = base.OUT
API = "https://commons.wikimedia.org/w/api.php"
UA = "query3-pose-sort/1.0 (GitHub Actions; contact via repository owner)"


def resolve_urls(meta):
    """Resolve exact Commons image URLs in batches through imageinfo."""
    filenames = []
    qid_for_title = {}
    for qid in base.QIDS:
        fn = meta.get(qid, {}).get("commons_filename")
        if fn:
            title = "File:" + fn
            filenames.append(title)
            qid_for_title[title] = qid

    resolved = {}
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    for start in range(0, len(filenames), 40):
        batch = filenames[start:start+40]
        params = {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "iiurlwidth": 1600,
            "titles": "|".join(batch),
        }
        for attempt in range(5):
            r = session.get(API, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(min(5 * (attempt + 1), 20))
                continue
            r.raise_for_status()
            data = r.json()
            break
        else:
            continue

        for page in data.get("query", {}).get("pages", []):
            title = page.get("title", "")
            qid = qid_for_title.get(title)
            if not qid:
                continue
            ii = (page.get("imageinfo") or [{}])[0]
            # Prefer an explicit thumbnail URL. Fall back to original only when needed.
            resolved[qid] = {
                "url": ii.get("thumburl") or ii.get("url"),
                "mime": ii.get("thumbmime") or ii.get("mime") or "",
                "width": ii.get("thumbwidth") or ii.get("width"),
                "height": ii.get("thumbheight") or ii.get("height"),
            }
        print(f"resolved {min(start+40, len(filenames))}/{len(filenames)}", flush=True)
        time.sleep(0.35)
    return resolved


def fetch_one(i, qid, m, info):
    label = m.get("label", qid)
    filename = m.get("commons_filename")
    stem = f"{i:04d}_{base.safe_slug(label)}_{qid}"
    if not filename:
        return qid, label, filename, None, "", "no P18 image on Wikidata"
    if not info or not info.get("url"):
        return qid, label, filename, None, "", "Wikimedia API did not return an image URL"

    url = info["url"]
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    last = None
    for attempt in range(4):
        try:
            r = sess.get(url, timeout=20)
            if r.status_code == 429:
                time.sleep(min(4 * (attempt + 1), 15))
                continue
            r.raise_for_status()
            ctype = r.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if not ctype.startswith("image/"):
                raise RuntimeError(f"not an image: {ctype}")
            ext = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/tiff": ".tif",
            }.get(ctype, Path(filename).suffix.lower() or ".img")
            path = OUT / "_downloads" / f"{stem}{ext}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
            return qid, label, filename, path, url, ""
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    return qid, label, filename, None, url, str(last)[:500]


def main():
    for d in ("front", "three_quarter", "side", "uncertain", "_downloads"):
        (OUT / d).mkdir(parents=True, exist_ok=True)

    meta = base.entity_metadata(base.QIDS)
    resolved = resolve_urls(meta)

    fetched = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {
            ex.submit(fetch_one, i, qid, meta.get(qid, {}), resolved.get(qid)): (i, qid)
            for i, qid in enumerate(base.QIDS, 1)
        }
        done = 0
        for fut in as_completed(futs):
            _, qid = futs[fut]
            fetched[qid] = fut.result()
            done += 1
            if done % 25 == 0 or done == len(futs):
                ok = sum(1 for v in fetched.values() if v[3] is not None)
                print(f"downloaded/attempted {done}/{len(futs)}; ok={ok}", flush=True)

    rows = []
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=5,
        refine_landmarks=False,
        min_detection_confidence=0.30,
    ) as mesh:
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
            try:
                p.unlink()
            except OSError:
                pass
        try:
            dl.rmdir()
        except OSError:
            pass

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
        "Image URLs were resolved through the Wikimedia Commons imageinfo API in batches.\n"
        "Pose bins: front <15 degrees, three-quarter 15-50 degrees, side >=50 degrees.\n"
        "Near-threshold or undetected faces are placed in uncertain.\n"
        "For multi-person photos, the largest detected face is treated as the subject.\n"
        "See manifest.csv for exact sources, yaw estimates, and classifications.\n",
        encoding="utf-8",
    )
    print("COUNTS", counts, "errors", errors, flush=True)


if __name__ == "__main__":
    main()
