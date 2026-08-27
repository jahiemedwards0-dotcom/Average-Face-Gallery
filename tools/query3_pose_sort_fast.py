from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import quote

import query3_pose_sort as base


def fast_download_commons(filename, dest_base):
    # MediaWiki's width parameter requests a display-sized derivative instead
    # of a potentially enormous original. 1800 px is more than enough for
    # face-mesh pose estimation and keeps the final dataset practical.
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(filename, safe="") + "?width=1800"
    last = None
    ext_for_type = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/tiff": ".tif",
    }
    for attempt in range(2):
        try:
            r = base.SESSION.get(url, timeout=35, allow_redirects=True)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if not ctype.startswith("image/"):
                raise RuntimeError(f"not an image: {ctype}")
            suffix = ext_for_type.get(ctype, Path(filename).suffix.lower() or ".jpg")
            path = dest_base.with_suffix(suffix)
            path.write_bytes(r.content)
            return path, url
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(last)


base.download_commons = fast_download_commons

if __name__ == "__main__":
    base.main()
