"""Path allowlist + SSRF-safe URL fetching for the MCP server.

The fetch logic mirrors 04-web-app/backend/app/security.py (kept as a copy so
each project stays self-contained)."""

import ipaddress
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests

MAX_DOWNLOAD_BYTES = int(os.getenv("MD_MCP_MAX_DOWNLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_REDIRECTS = 5
FETCH_TIMEOUT = int(os.getenv("MD_MCP_FETCH_TIMEOUT", "30"))
ACCEPT_HEADER = "text/markdown, text/html;q=0.9, text/plain;q=0.8, */*;q=0.1"
USER_AGENT = "markdrop-mcp/0.1 (Dhiva Labs)"


class AccessDeniedError(PermissionError):
    pass


class UnsafeUrlError(ValueError):
    pass


# --- File roots allowlist ----------------------------------------------------

class Roots:
    """Canonical-path allowlist. A path is readable/writable only when its
    fully-resolved form (symlinks followed) sits under one of the roots."""

    def __init__(self, roots: list[str | Path] | None = None):
        raw: list[str | Path] = list(roots or [])
        if not raw:
            env = os.getenv("MD_MCP_ROOTS", "")
            if env:
                raw = [r for r in env.split(":") if r.strip()]
            else:
                raw = [
                    Path.cwd(),
                    Path.home() / "Documents",
                    Path.home() / "Downloads",
                ]
        self.roots = [Path(r).expanduser().resolve() for r in raw]

    def resolve(self, path: str | Path) -> Path:
        p = Path(path).expanduser().resolve()
        for root in self.roots:
            if p == root or p.is_relative_to(root):
                return p
        raise AccessDeniedError(
            f"Path {p} is outside the allowed roots: "
            + ", ".join(str(r) for r in self.roots)
            + ". Start the server with additional --root arguments to widen access."
        )

    def describe(self) -> str:
        return ", ".join(str(r) for r in self.roots)


# --- SSRF-safe URL fetch -----------------------------------------------------

def _assert_public_host(hostname: str) -> None:
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
        raise UnsafeUrlError(
            f"Only http/https URLs are allowed here, got: {parsed.scheme or 'none'}"
        )
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no host")
    if os.getenv("MD_MCP_ALLOW_PRIVATE_URLS", "").lower() not in ("1", "true", "yes"):
        _assert_public_host(parsed.hostname)
    return url


@dataclass
class FetchedUrl:
    url: str
    data: bytes
    mimetype: str | None = None
    charset: str | None = None
    filename: str | None = None


def fetch_url_safe(url: str) -> FetchedUrl:
    sess = requests.Session()
    headers = {"Accept": ACCEPT_HEADER, "User-Agent": USER_AGENT}
    current = validate_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        resp = sess.get(
            current, headers=headers, stream=True, timeout=FETCH_TIMEOUT,
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
            raise UnsafeUrlError(f"Resource is {declared} bytes; limit is {MAX_DOWNLOAD_BYTES}")

        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                resp.close()
                raise UnsafeUrlError(f"Download exceeded the {MAX_DOWNLOAD_BYTES}-byte limit")
            chunks.append(chunk)

        mimetype = charset = None
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
            url=str(resp.url), data=b"".join(chunks),
            mimetype=mimetype, charset=charset, filename=filename,
        )
    raise UnsafeUrlError(f"Too many redirects (>{MAX_REDIRECTS})")
