"""Request gating: SSRF-safe URL fetching, API key check, simple per-IP rate limit."""

import ipaddress
import os
import socket
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin

import requests

MAX_DOWNLOAD_BYTES = int(os.getenv("MD_MAX_DOWNLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_REDIRECTS = 5
FETCH_TIMEOUT = int(os.getenv("MD_FETCH_TIMEOUT", "30"))

# Same Accept preference markitdown's own session uses
ACCEPT_HEADER = "text/markdown, text/html;q=0.9, text/plain;q=0.8, */*;q=0.1"
USER_AGENT = "md-files-dhivalabs/0.1 (+conversion service)"


class UnsafeUrlError(ValueError):
    pass


class DownloadTooLargeError(ValueError):
    pass


def _assert_public_host(hostname: str) -> None:
    """Resolve hostname and reject anything that lands on a private/reserved address."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise UnsafeUrlError(f"Could not resolve host: {hostname}") from e

    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            raise UnsafeUrlError(
                f"URL host {hostname} resolves to a non-public address ({addr})"
            )


def validate_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Only http/https URLs are allowed, got: {parsed.scheme or 'none'}")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no host")
    if os.getenv("MD_ALLOW_PRIVATE_URLS", "").lower() not in ("1", "true", "yes"):
        _assert_public_host(parsed.hostname)
    return url


@dataclass
class FetchedUrl:
    url: str  # final URL after redirects
    data: bytes
    mimetype: str | None = None
    charset: str | None = None
    filename: str | None = None


def fetch_url_safe(url: str, session: requests.Session | None = None) -> FetchedUrl:
    """Download a URL with manual redirect handling so every hop is SSRF-checked,
    and with a hard size cap."""
    sess = session or requests.Session()
    headers = {"Accept": ACCEPT_HEADER, "User-Agent": USER_AGENT}

    current = validate_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        resp = sess.get(
            current,
            headers=headers,
            stream=True,
            timeout=FETCH_TIMEOUT,
            allow_redirects=False,
        )
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("location")
            resp.close()
            if not location:
                raise UnsafeUrlError("Redirect without Location header")
            current = validate_url(urljoin(current, location))
            continue

        resp.raise_for_status()

        declared = resp.headers.get("content-length")
        if declared and int(declared) > MAX_DOWNLOAD_BYTES:
            resp.close()
            raise DownloadTooLargeError(
                f"Resource is {declared} bytes; limit is {MAX_DOWNLOAD_BYTES}"
            )

        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                resp.close()
                raise DownloadTooLargeError(
                    f"Download exceeded the {MAX_DOWNLOAD_BYTES}-byte limit"
                )
            chunks.append(chunk)

        mimetype = None
        charset = None
        if "content-type" in resp.headers:
            parts = resp.headers["content-type"].split(";")
            mimetype = parts.pop(0).strip() or None
            for part in parts:
                part = part.strip()
                if part.startswith("charset="):
                    charset = part.split("=", 1)[1].strip() or None

        filename = None
        cd = resp.headers.get("content-disposition", "")
        if "filename=" in cd:
            filename = cd.split("filename=", 1)[1].split(";")[0].strip("\"' ")

        return FetchedUrl(
            url=str(resp.url),
            data=b"".join(chunks),
            mimetype=mimetype,
            charset=charset,
            filename=filename,
        )

    raise UnsafeUrlError(f"Too many redirects (>{MAX_REDIRECTS})")


# --- API key -----------------------------------------------------------------

def api_key_ok(provided: str | None) -> bool:
    expected = os.getenv("MD_API_KEY", "")
    if not expected:
        return True  # auth disabled
    return provided is not None and provided == expected


# --- Rate limiting (tiny in-memory token bucket per IP) ----------------------

@dataclass
class _Bucket:
    tokens: float
    updated: float = field(default_factory=time.monotonic)


class RateLimiter:
    def __init__(self, rate_per_minute: int | None = None, burst: int | None = None):
        self.rate = (rate_per_minute or int(os.getenv("MD_RATE_PER_MINUTE", "30"))) / 60.0
        self.burst = burst or int(os.getenv("MD_RATE_BURST", "10"))
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=float(self.burst))
            self._buckets[key] = bucket
        bucket.tokens = min(self.burst, bucket.tokens + (now - bucket.updated) * self.rate)
        bucket.updated = now
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False
