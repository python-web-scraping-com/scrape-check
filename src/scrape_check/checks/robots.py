from __future__ import annotations

from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from scrape_check.fetch import SCRAPE_CHECK_UA
from scrape_check.models import RobotsInfo


def check(client: httpx.Client, url: str, *, user_agent: str = "*") -> RobotsInfo:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return RobotsInfo(fetched=False, url="", error="invalid URL")

    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}/", "/robots.txt")

    try:
        resp = client.get(robots_url, headers={"User-Agent": SCRAPE_CHECK_UA})
    except Exception as exc:
        return RobotsInfo(fetched=False, url=robots_url, error=f"{type(exc).__name__}: {exc}")

    if resp.status_code == 404:
        # Per RFC 9309: no robots.txt means everything is allowed.
        return RobotsInfo(fetched=True, url=robots_url, status=404, allowed=True)
    if resp.status_code >= 400:
        return RobotsInfo(
            fetched=True,
            url=robots_url,
            status=resp.status_code,
            error=f"HTTP {resp.status_code}",
        )

    rp = RobotFileParser()
    rp.parse(resp.text.splitlines())

    allowed = rp.can_fetch(user_agent, url)
    crawl_delay: float | None = None
    try:
        cd = rp.crawl_delay(user_agent)
        if cd is not None:
            crawl_delay = float(cd)
    except Exception:
        crawl_delay = None

    sitemaps = list(rp.site_maps() or [])

    return RobotsInfo(
        fetched=True,
        url=robots_url,
        status=resp.status_code,
        allowed=allowed,
        crawl_delay=crawl_delay,
        sitemaps=sitemaps,
    )
