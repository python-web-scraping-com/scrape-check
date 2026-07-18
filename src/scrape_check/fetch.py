"""HTTP fetcher used by all checks. One shared client per run."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
SCRAPE_CHECK_UA = "scrape-check/0.2 (+https://github.com/python-web-scraping-com/scrape-check)"


@dataclass
class FetchResult:
    request_url: str
    final_url: str
    status: int
    http_version: str
    headers: httpx.Headers
    cookies: httpx.Cookies
    text: str
    elapsed_ms: int
    redirects: list[str]


def make_client(
    *,
    timeout: float = 15.0,
    user_agent: str = DEFAULT_UA,
    follow_redirects: bool = True,
) -> httpx.Client:
    return httpx.Client(
        http2=False,  # http2 is optional; keep deps minimal
        timeout=timeout,
        follow_redirects=follow_redirects,
        # Don't set Accept-Encoding manually — let httpx advertise only the
        # codecs it can actually decode (gzip/deflate, plus br if brotli is
        # installed). Advertising "br" without a decoder gives you garbage.
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )


def fetch(client: httpx.Client, url: str) -> FetchResult:
    start = time.monotonic()
    resp = client.get(url)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    redirects = [str(r.url) for r in resp.history]
    return FetchResult(
        request_url=url,
        final_url=str(resp.url),
        status=resp.status_code,
        http_version=resp.http_version,
        headers=resp.headers,
        cookies=resp.cookies,
        text=resp.text,
        elapsed_ms=elapsed_ms,
        redirects=redirects,
    )
