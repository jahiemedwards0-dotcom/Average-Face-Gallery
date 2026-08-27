from __future__ import annotations

import hashlib
import html
import json
import os
import re
import socket
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote

import requests
from PIL import Image, UnidentifiedImageError


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
TRANSIENT_HTTP = {429, 500, 502, 503, 504}
DEFAULT_WAITS = (60, 120, 300, 600)


class RateLimitStop(RuntimeError):
    """Raised after repeated consecutive Wikimedia HTTP 429 responses."""


@dataclass
class DownloadResult:
    values: dict[str, Any]
    stop_requested: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", html.unescape(value))
    return re.sub(r"\s+", " ", text).strip()


def safe_ext_from_format(fmt: str | None) -> str:
    fmt = (fmt or "").lower()
    return {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp", "gif": ".gif", "tiff": ".tif"}.get(fmt, ".img")


class WikimediaDownloader:
    """Serial, rate-limit-aware Wikimedia Commons metadata resolver and image downloader."""

    def __init__(
        self,
        *,
        repo_url: str,
        contact: str,
        thumbnail_width: int = 500,
        delay_seconds: float = 2.0,
        timeout_seconds: int = 45,
        backoff_waits: Iterable[int] = DEFAULT_WAITS,
        max_consecutive_429: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        self.repo_url = repo_url.rstrip("/")
        self.contact = contact.strip()
        self.thumbnail_width = int(thumbnail_width)
        self.delay_seconds = float(delay_seconds)
        self.timeout_seconds = int(timeout_seconds)
        self.backoff_waits = tuple(int(x) for x in backoff_waits)
        self.max_consecutive_429 = int(max_consecutive_429)
        self.session = session or requests.Session()
        contact_part = f"; contact: {self.contact}" if self.contact else ""
        self.user_agent = f"MestizoFaceHarvester/1.0 ({self.repo_url}{contact_part})"
        self.session.headers.update({"User-Agent": self.user_agent})
        self._last_image_request_at: float | None = None
        self._consecutive_429 = 0

    def _respect_image_delay(self) -> None:
        if self._last_image_request_at is None:
            return
        elapsed = time.monotonic() - self._last_image_request_at
        remaining = self.delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    @staticmethod
    def _retry_after_seconds(response: requests.Response) -> int | None:
        raw = response.headers.get("Retry-After", "").strip()
        if not raw:
            return None
        try:
            return max(0, int(raw))
        except ValueError:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return max(0, int((dt - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                return None

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        stream: bool = False,
        image_request: bool = False,
    ) -> tuple[requests.Response | None, int, str]:
        waits = self.backoff_waits or DEFAULT_WAITS
        last_error = ""
        for attempt in range(len(waits) + 1):
            if image_request:
                self._respect_image_delay()
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    timeout=self.timeout_seconds,
                    stream=stream,
                    allow_redirects=True,
                )
                if image_request:
                    self._last_image_request_at = time.monotonic()
            except (requests.ConnectionError, requests.Timeout, socket.gaierror) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                # DNS failure generally means there is no usable network route. Do not turn it
                # into minutes of exponential sleeping; the orchestrator can checkpoint and retry later.
                if "NameResolutionError" in last_error or "name resolution" in last_error.lower():
                    return None, attempt, last_error
                if attempt >= len(waits):
                    return None, attempt, last_error
                time.sleep(waits[attempt])
                continue

            if response.status_code == 429:
                self._consecutive_429 += 1
                if self._consecutive_429 >= self.max_consecutive_429:
                    retry_after = self._retry_after_seconds(response)
                    raise RateLimitStop(f"Repeated HTTP 429; Retry-After={retry_after!r}")
            else:
                self._consecutive_429 = 0

            if response.status_code not in TRANSIENT_HTTP:
                return response, attempt, ""
            if attempt >= len(waits):
                return response, attempt, f"HTTP {response.status_code} after {attempt} retries"

            retry_after = self._retry_after_seconds(response)
            wait = retry_after if retry_after is not None else waits[attempt]
            time.sleep(wait)

        return None, len(waits), last_error or "request failed"

    @staticmethod
    def _title_key(title: str) -> str:
        return title.replace("_", " ").strip().casefold()

    def _metadata_from_page(self, page: dict[str, Any], retries: int, requested_title: str) -> dict[str, Any]:
        ii = (page.get("imageinfo") or [{}])[0]
        if not ii or "url" not in ii:
            return {
                "ok": False,
                "http_status": 200,
                "retry_count": retries,
                "error_message": "Commons file missing" if page.get("missing") is not None else "No imageinfo returned",
            }
        ext = ii.get("extmetadata") or {}
        def ev(key: str) -> str:
            item = ext.get(key) or {}
            return str(item.get("value") or "")
        canonical_title = page.get("title") or requested_title
        file_name = canonical_title[5:] if canonical_title.lower().startswith("file:") else canonical_title
        return {
            "ok": True,
            "http_status": 200,
            "retry_count": retries,
            "error_message": "",
            "commons_file_page_url": f"https://commons.wikimedia.org/wiki/File:{quote(file_name.replace(' ', '_'), safe='')}",
            "resolved_thumbnail_url": ii.get("thumburl") or ii.get("url") or "",
            "original_file_url": ii.get("url") or "",
            "license_name": strip_html(ev("LicenseShortName") or ev("License")),
            "license_url": strip_html(ev("LicenseUrl")),
            "artist": strip_html(ev("Artist")),
            "credit": strip_html(ev("Credit")),
            "attribution": strip_html(ev("Attribution") or ev("AttributionRequired")),
            "commons_description_url": ii.get("descriptionurl") or "",
            "commons_mime": ii.get("mime") or "",
            "commons_original_width": ii.get("width") or "",
            "commons_original_height": ii.get("height") or "",
            "extmetadata_json": json.dumps(ext, ensure_ascii=False, separators=(",", ":")),
        }

    def resolve_commons_metadata_batch(self, commons_filenames: list[str]) -> dict[str, dict[str, Any]]:
        """Resolve a small filename batch with one Commons API request; never parallelizes requests."""
        filenames = [str(x or "").strip() for x in commons_filenames]
        result: dict[str, dict[str, Any]] = {}
        valid = [x for x in filenames if x]
        for empty in [x for x in filenames if not x]:
            result[empty] = {"ok": False, "http_status": "", "retry_count": 0, "error_message": "Missing commons_filename"}
        if not valid:
            return result
        titles = [x if x.lower().startswith("file:") else f"File:{x}" for x in valid]
        params = {
            "action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo",
            "titles": "|".join(titles), "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": self.thumbnail_width, "redirects": 1,
        }
        response, retries, err = self._request("GET", COMMONS_API, params=params)
        if response is None:
            return {x: {"ok": False, "http_status": "", "retry_count": retries, "error_message": err} for x in valid}
        if response.status_code != 200:
            msg = f"Commons API HTTP {response.status_code}: {response.text[:300]}"
            return {x: {"ok": False, "http_status": response.status_code, "retry_count": retries, "error_message": msg} for x in valid}
        try:
            payload = response.json()
            query = payload.get("query", {})
            pages = query.get("pages") or []
        except (ValueError, TypeError) as exc:
            msg = f"Metadata parse error: {exc}"
            return {x: {"ok": False, "http_status": 200, "retry_count": retries, "error_message": msg} for x in valid}

        aliases: dict[str, str] = {}
        for section in ("normalized", "redirects", "converted"):
            for item in query.get(section, []) or []:
                if item.get("from") and item.get("to"):
                    aliases[self._title_key(str(item["from"]))] = self._title_key(str(item["to"]))
        pages_by_title = {self._title_key(str(page.get("title") or "")): page for page in pages}

        for filename, requested_title in zip(valid, titles):
            key = self._title_key(requested_title)
            seen: set[str] = set()
            while key in aliases and key not in seen:
                seen.add(key)
                key = aliases[key]
            page = pages_by_title.get(key)
            if page is None:
                result[filename] = {
                    "ok": False, "http_status": 200, "retry_count": retries,
                    "error_message": "Commons API returned no page for requested file",
                }
            else:
                result[filename] = self._metadata_from_page(page, retries, requested_title)
        return result

    def resolve_commons_metadata(self, commons_filename: str) -> dict[str, Any]:
        return self.resolve_commons_metadata_batch([commons_filename]).get(
            str(commons_filename or "").strip(),
            {"ok": False, "http_status": "", "retry_count": 0, "error_message": "Metadata resolution failed"},
        )

    @staticmethod
    def validate_image(path: Path) -> dict[str, Any]:
        try:
            with Image.open(path) as im:
                im.load()
                width, height = im.size
                fmt = im.format or ""
            if width <= 0 or height <= 0:
                raise ValueError("non-positive image dimensions")
            return {"ok": True, "width": width, "height": height, "image_format": fmt}
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            return {"ok": False, "error_message": f"Image decode failed: {exc}"}

    def download_one(
        self,
        row: dict[str, Any],
        *,
        unique_dir: Path,
        known_hashes: dict[str, str],
        metadata: dict[str, Any] | None = None,
        checkpoint: Callable[[dict[str, Any]], None] | None = None,
    ) -> DownloadResult:
        out: dict[str, Any] = {
            "download_attempted": True,
            "download_status": "download_failed",
            "http_status": "",
            "retry_count": 0,
            "error_message": "",
            "local_filename": "",
            "width": "",
            "height": "",
            "image_format": "",
            "sha256": "",
            "duplicate_status": "unique",
            "duplicate_of_hash": "",
            "download_timestamp": "",
            "reused_resumed": False,
        }
        filename = str(row.get("commons_filename") or "").strip()
        if not filename:
            out["error_message"] = "Missing commons_filename"
            return DownloadResult(out)

        metadata = metadata if metadata is not None else self.resolve_commons_metadata(filename)
        out.update({k: v for k, v in metadata.items() if k != "ok"})
        if not metadata.get("ok"):
            return DownloadResult(out)

        thumb_url = str(metadata.get("resolved_thumbnail_url") or "")
        if not thumb_url:
            out["error_message"] = "No resolved thumbnail URL"
            return DownloadResult(out)

        unique_dir.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_name = tempfile.mkstemp(prefix="download_", suffix=".part", dir=unique_dir)
        os.close(tmp_fd)
        tmp_path = Path(tmp_name)
        try:
            response, retries, err = self._request("GET", thumb_url, stream=True, image_request=True)
            out["retry_count"] = int(out.get("retry_count") or 0) + retries
            if response is None:
                out["error_message"] = err
                return DownloadResult(out)
            out["http_status"] = response.status_code
            if response.status_code != 200:
                out["error_message"] = f"Image HTTP {response.status_code}: {response.text[:200] if not response.raw.closed else ''}"
                return DownloadResult(out)
            with tmp_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        f.write(chunk)
            validation = self.validate_image(tmp_path)
            if not validation.get("ok"):
                out["download_status"] = "rejected_decode"
                out["error_message"] = validation.get("error_message", "Image decode failed")
                return DownloadResult(out)
            digest = sha256_file(tmp_path)
            out.update(validation)
            out["sha256"] = digest
            out["download_timestamp"] = utc_now()

            if digest in known_hashes:
                out["download_status"] = "verified_duplicate"
                out["duplicate_status"] = "duplicate_file"
                out["duplicate_of_hash"] = digest
                out["local_filename"] = known_hashes[digest]
                tmp_path.unlink(missing_ok=True)
                if checkpoint:
                    checkpoint(out)
                return DownloadResult(out)

            ext = safe_ext_from_format(str(validation.get("image_format") or ""))
            final_path = unique_dir / f"{digest}{ext}"
            os.replace(tmp_path, final_path)
            known_hashes[digest] = str(final_path)
            out["download_status"] = "verified"
            out["duplicate_status"] = "unique"
            out["local_filename"] = str(final_path)
            if checkpoint:
                checkpoint(out)
            return DownloadResult(out)
        finally:
            tmp_path.unlink(missing_ok=True)
