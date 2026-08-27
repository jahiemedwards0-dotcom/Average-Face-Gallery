from __future__ import annotations

import hashlib
import html
import io
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import quote, unquote, urlparse

import requests
from PIL import Image, UnidentifiedImageError


TRANSIENT = {429, 500, 502, 503, 504}


class StopForRateLimit(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_html(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def safe_ext(fmt: str, fallback_url: str = "") -> str:
    fmt = (fmt or "").lower()
    mapping = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp", "gif": ".gif", "tiff": ".tif"}
    if fmt in mapping:
        return mapping[fmt]
    suffix = Path(urlparse(fallback_url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"} else ".img"


def derive_commons_filename(row: Dict[str, Any]) -> str:
    filename = str(row.get("commons_filename") or "").strip()
    if filename and filename.lower() != "nan":
        return filename.removeprefix("File:")
    for key in ("image_url",):
        url = str(row.get(key) or "").strip()
        if not url:
            continue
        path = unquote(urlparse(url).path)
        if "/Special:Redirect/file/" in path:
            return path.split("/Special:Redirect/file/", 1)[1]
        if "/wiki/Special:Redirect/file/" in path:
            return path.split("/wiki/Special:Redirect/file/", 1)[1]
        if "/wikipedia/commons/" in path or "/commons/" in path:
            base = Path(path).name
            if base:
                return base
    return ""


@dataclass
class WikimediaClient:
    user_agent: str
    delay_seconds: float = 2.0
    metadata_batch_size: int = 10
    max_retries: int = 4
    timeout_seconds: int = 45
    consecutive_429_stop: int = 3

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent, "Accept": "*/*"})
        self.last_image_request_at = 0.0
        self.consecutive_429 = 0
        self.http_image_requests = 0

    def _wait_for_image_slot(self) -> None:
        elapsed = time.monotonic() - self.last_image_request_at
        wait = self.delay_seconds - elapsed
        if wait > 0:
            time.sleep(wait)

    def _backoff_seconds(self, response: Optional[requests.Response], retry: int) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(float(retry_after), 1.0)
                except ValueError:
                    pass
        schedule = [60, 120, 300, 600]
        return float(schedule[min(retry, len(schedule) - 1)])

    def request(self, method: str, url: str, *, is_image: bool = False, **kwargs: Any) -> Tuple[requests.Response, int]:
        retry = 0
        while True:
            if is_image:
                self._wait_for_image_slot()
            try:
                if is_image:
                    self.http_image_requests += 1
                    self.last_image_request_at = time.monotonic()
                response = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
            except requests.RequestException:
                if retry >= self.max_retries:
                    raise
                time.sleep(min(2 ** retry * 5, 60))
                retry += 1
                continue

            if response.status_code == 429:
                self.consecutive_429 += 1
                if self.consecutive_429 >= self.consecutive_429_stop:
                    raise StopForRateLimit(
                        f"Stopped after {self.consecutive_429} consecutive HTTP 429 responses; checkpoint should be preserved."
                    )
            else:
                self.consecutive_429 = 0

            if response.status_code not in TRANSIENT:
                return response, retry

            if retry >= self.max_retries:
                return response, retry

            time.sleep(self._backoff_seconds(response, retry))
            retry += 1

    def _metadata_from_page(self, page: Dict[str, Any], thumb_width: int, retry: int, http_status: int) -> Dict[str, Any]:
        if page.get("missing"):
            return {
                "metadata_status": "missing",
                "metadata_http_status": http_status,
                "metadata_retry_count": retry,
                "error_message": "Commons file page missing",
            }
        info = (page.get("imageinfo") or [{}])[0]
        ext = info.get("extmetadata") or {}

        def em(key: str) -> str:
            item = ext.get(key) or {}
            return clean_html(item.get("value", ""))

        canonical_title = page.get("title") or ""
        page_filename = canonical_title.removeprefix("File:")
        file_page_url = "https://commons.wikimedia.org/wiki/File:" + quote(
            page_filename.replace(" ", "_"), safe="()_,-."
        )
        return {
            "metadata_status": "resolved",
            "metadata_http_status": http_status,
            "metadata_retry_count": retry,
            "commons_filename": page_filename,
            "commons_file_page_url": file_page_url,
            "resolved_thumbnail_url": info.get("thumburl") or info.get("url") or "",
            "original_file_url": info.get("url") or "",
            "source": em("Source") or em("ImageDescription"),
            "license_name": em("LicenseShortName") or em("UsageTerms"),
            "license_url": em("LicenseUrl"),
            "artist": em("Artist"),
            "credit": em("Credit"),
            "attribution": em("Attribution"),
            "usage_terms": em("UsageTerms"),
            "commons_width": info.get("width"),
            "commons_height": info.get("height"),
            "commons_mime": info.get("mime"),
        }

    def resolve_metadata_batch(self, filenames: Iterable[str], thumb_width: int = 500) -> Dict[str, Dict[str, Any]]:
        ordered = []
        seen = set()
        for filename in filenames:
            filename = str(filename or "").strip().removeprefix("File:")
            if filename and filename not in seen:
                ordered.append(filename)
                seen.add(filename)
        results: Dict[str, Dict[str, Any]] = {}
        for filename in filenames:
            if not str(filename or "").strip():
                results[str(filename or "")] = {
                    "metadata_status": "missing_commons_filename",
                    "error_message": "Missing Commons filename",
                }
        if not ordered:
            return results

        # Keep metadata requests in deliberately small, serial API batches.
        batch_size = max(1, min(int(self.metadata_batch_size), 25))
        api = "https://commons.wikimedia.org/w/api.php"
        for offset in range(0, len(ordered), batch_size):
            batch = ordered[offset : offset + batch_size]
            requested_titles = [f"File:{x}" for x in batch]
            params = {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "imageinfo",
                "titles": "|".join(requested_titles),
                "iiprop": "url|size|mime|extmetadata",
                "iiurlwidth": int(thumb_width),
                "redirects": 1,
            }
            response, retry = self.request("GET", api, params=params)
            if response.status_code != 200:
                for filename in batch:
                    results[filename] = {
                        "metadata_status": "http_error",
                        "metadata_http_status": response.status_code,
                        "metadata_retry_count": retry,
                        "error_message": f"Commons metadata HTTP {response.status_code}",
                    }
                continue
            try:
                query = response.json().get("query", {})
                pages = query.get("pages", [])
                page_by_title = {str(p.get("title", "")).replace("_", " "): p for p in pages}

                remap: Dict[str, str] = {}
                for item in query.get("normalized", []) or []:
                    remap[str(item.get("from", "")).replace("_", " ")] = str(item.get("to", "")).replace("_", " ")
                for item in query.get("redirects", []) or []:
                    remap[str(item.get("from", "")).replace("_", " ")] = str(item.get("to", "")).replace("_", " ")

                for filename, requested in zip(batch, requested_titles):
                    title = requested.replace("_", " ")
                    visited = set()
                    while title in remap and title not in visited:
                        visited.add(title)
                        title = remap[title]
                    page = page_by_title.get(title)
                    if page is None:
                        # Conservative fallback: use a unique page whose normalized filename matches.
                        wanted = filename.replace("_", " ").casefold()
                        matches = [
                            p for p in pages
                            if str(p.get("title", "")).removeprefix("File:").replace("_", " ").casefold() == wanted
                        ]
                        page = matches[0] if len(matches) == 1 else None
                    if page is None:
                        results[filename] = {
                            "metadata_status": "parse_error",
                            "metadata_http_status": response.status_code,
                            "metadata_retry_count": retry,
                            "error_message": "Commons metadata response did not map uniquely to requested filename",
                        }
                    else:
                        results[filename] = self._metadata_from_page(
                            page, thumb_width, retry, response.status_code
                        )
            except Exception as exc:
                for filename in batch:
                    results[filename] = {
                        "metadata_status": "parse_error",
                        "metadata_http_status": response.status_code,
                        "metadata_retry_count": retry,
                        "error_message": f"Commons metadata parse error: {exc}",
                    }
        return results

    def resolve_metadata(self, filename: str, thumb_width: int = 500) -> Dict[str, Any]:
        filename = str(filename or "").strip().removeprefix("File:")
        return self.resolve_metadata_batch([filename], thumb_width).get(
            filename,
            {"metadata_status": "missing_commons_filename", "error_message": "Missing Commons filename"},
        )

    def download_and_validate(
        self,
        url: str,
        destination_dir: Path,
        candidate_id: str,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "download_status": "download_failed",
            "http_status": "",
            "retry_count": 0,
            "error_message": "",
            "local_filename": "",
            "width": "",
            "height": "",
            "image_format": "",
            "sha256": "",
            "download_timestamp": "",
        }
        if not url:
            result["error_message"] = "No resolved thumbnail URL"
            return result

        try:
            response, retry = self.request("GET", url, is_image=True, stream=True)
            result["http_status"] = response.status_code
            result["retry_count"] = retry
        except StopForRateLimit:
            raise
        except requests.RequestException as exc:
            result["error_message"] = f"Network error: {exc}"
            return result

        if response.status_code != 200:
            result["error_message"] = f"Image HTTP {response.status_code}"
            return result

        data = response.content
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
            with Image.open(io.BytesIO(data)) as img:
                img.load()
                width, height = img.size
                fmt = (img.format or "").lower()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            result["error_message"] = f"Image decode failed: {exc}"
            result["download_status"] = "rejected_decode"
            return result

        digest = hashlib.sha256(data).hexdigest()
        ext = safe_ext(fmt, url)
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = destination_dir / f"{candidate_id}_{digest[:16]}{ext}"
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)

        result.update(
            {
                "download_status": "downloaded",
                "local_filename": str(target),
                "width": width,
                "height": height,
                "image_format": fmt,
                "sha256": digest,
                "download_timestamp": utc_now(),
                "error_message": "",
            }
        )
        return result


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
