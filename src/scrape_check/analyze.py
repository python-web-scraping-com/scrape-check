from __future__ import annotations

import httpx

from scrape_check.checks import antibot, http_info, rendering, robots
from scrape_check.fetch import DEFAULT_UA, fetch, make_client
from scrape_check.models import AntiBotInfo, RenderingInfo, Report
from scrape_check.recommend import build as build_recommendation


def analyze(url: str, *, timeout: float = 15.0, user_agent: str | None = None) -> Report:
    ua = user_agent or DEFAULT_UA
    with make_client(timeout=timeout, user_agent=ua) as client:
        robots_info = robots.check(client, url)

        try:
            result = fetch(client, url)
        except (httpx.RequestError, httpx.HTTPError) as exc:
            http_data = http_info.from_error(url, exc)
            antibot_data = AntiBotInfo()
            rendering_data = RenderingInfo(mode="unknown")
            return Report(
                target=url,
                http=http_data,
                robots=robots_info,
                antibot=antibot_data,
                rendering=rendering_data,
                recommendation=build_recommendation(http_data, robots_info, antibot_data, rendering_data),
            )

    http_data = http_info.from_fetch(result)
    antibot_data = antibot.detect(result)
    rendering_data = rendering.analyze(result)

    return Report(
        target=url,
        http=http_data,
        robots=robots_info,
        antibot=antibot_data,
        rendering=rendering_data,
        recommendation=build_recommendation(http_data, robots_info, antibot_data, rendering_data),
    )
