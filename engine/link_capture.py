"""Link metadata fetch for sb_capture_link."""
from __future__ import annotations
import re
import urllib.request
from urllib.parse import urlparse
from urllib.request import Request

_TIMEOUT = 5  # seconds


def _extract_og(html: str, prop: str) -> str:
    m = re.search(
        rf'<meta[^>]+property=["\']og:{prop}["\'][^>]+content=["\']([^"\']*)["\']',
        html,
        re.IGNORECASE,
    )
    if not m:
        m = re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']og:{prop}["\']',
            html,
            re.IGNORECASE,
        )
    return m.group(1).strip() if m else ""


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def fetch_link_metadata(url: str) -> dict:
    """Fetch og:title/og:description from URL. Never raises — falls back to domain on error.

    Args:
        url: The URL to fetch metadata from.

    Returns:
        Dict with keys 'title' (str) and 'description' (str).
        On any error, returns {"title": "<hostname>", "description": ""}.
    """
    hostname = urlparse(url).hostname or url
    try:
        req = Request(url, headers={"User-Agent": "second-brain/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read(65536)  # read at most 64KB
            html = raw.decode("utf-8", errors="replace")
        title = _extract_og(html, "title") or _extract_title(html) or hostname
        description = _extract_og(html, "description")
        return {"title": title, "description": description}
    except Exception:
        return {"title": hostname, "description": ""}
