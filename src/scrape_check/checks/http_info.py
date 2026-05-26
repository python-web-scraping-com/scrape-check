from __future__ import annotations

from scrape_check.fetch import FetchResult
from scrape_check.models import HttpInfo

# Common rate-limit header families. Stored in lowercase.
_RATE_LIMIT_PREFIXES = (
    "x-ratelimit-",
    "ratelimit-",
    "x-rate-limit-",
)


def from_fetch(result: FetchResult) -> HttpInfo:
    rl: dict[str, str] = {}
    for k, v in result.headers.items():
        kl = k.lower()
        if kl.startswith(_RATE_LIMIT_PREFIXES) or kl == "retry-after":
            rl[k] = v

    content_length: int | None = None
    if cl := result.headers.get("content-length"):
        try:
            content_length = int(cl)
        except ValueError:
            content_length = None

    return HttpInfo(
        url=result.request_url,
        final_url=result.final_url,
        status=result.status,
        http_version=result.http_version,
        server=result.headers.get("server"),
        content_type=result.headers.get("content-type"),
        content_length=content_length,
        elapsed_ms=result.elapsed_ms,
        redirects=result.redirects,
        rate_limit_headers=rl,
        retry_after=result.headers.get("retry-after"),
    )


def from_error(url: str, exc: Exception) -> HttpInfo:
    return HttpInfo(
        url=url,
        final_url=url,
        status=0,
        http_version="",
        server=None,
        content_type=None,
        content_length=None,
        elapsed_ms=0,
        error=f"{type(exc).__name__}: {exc}",
    )
