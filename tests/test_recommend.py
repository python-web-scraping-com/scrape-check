from scrape_check.models import AntiBotInfo, HttpInfo, RenderingInfo, RobotsInfo
from scrape_check.recommend import build


def _http(**overrides) -> HttpInfo:
    defaults = dict(
        url="https://example.com/",
        final_url="https://example.com/",
        status=200,
        http_version="HTTP/1.1",
        server="nginx",
        content_type="text/html",
        content_length=1000,
        elapsed_ms=50,
    )
    defaults.update(overrides)
    return HttpInfo(**defaults)


def test_robots_disallow_blocks_everything():
    rec = build(
        _http(),
        RobotsInfo(fetched=True, url="https://example.com/robots.txt", allowed=False),
        AntiBotInfo(),
        RenderingInfo(mode="ssr"),
    )
    assert rec.strategy == "do-not-scrape"


def test_clean_ssr_site_recommends_requests():
    rec = build(
        _http(),
        RobotsInfo(fetched=True, url="https://example.com/robots.txt", allowed=True),
        AntiBotInfo(),
        RenderingInfo(mode="ssr"),
    )
    assert rec.strategy == "requests"


def test_cloudflare_cdn_only_recommends_stealth_headers_not_headless():
    rec = build(
        _http(),
        RobotsInfo(fetched=True, url="https://example.com/robots.txt", allowed=True),
        AntiBotInfo(cdns=["Cloudflare (CDN)"], signals={"Cloudflare (CDN)": ["cf-ray"]}),
        RenderingInfo(mode="ssr"),
    )
    assert rec.strategy == "stealth-headers"


def test_active_cloudflare_bot_management_recommends_headless():
    rec = build(
        _http(),
        RobotsInfo(fetched=True, url="https://example.com/robots.txt", allowed=True),
        AntiBotInfo(
            cdns=["Cloudflare (CDN)"],
            bot_defense=["Cloudflare Bot Management"],
            signals={"Cloudflare Bot Management": ["__cf_bm cookie"]},
        ),
        RenderingInfo(mode="ssr"),
    )
    assert rec.strategy == "headless"


def test_csr_recommends_headless():
    rec = build(
        _http(),
        RobotsInfo(fetched=True, url="https://example.com/robots.txt", allowed=True),
        AntiBotInfo(),
        RenderingInfo(mode="csr", framework="React"),
    )
    assert rec.strategy == "headless"


def test_hybrid_recommends_stealth_headers():
    rec = build(
        _http(),
        RobotsInfo(fetched=True, url="https://example.com/robots.txt", allowed=True),
        AntiBotInfo(),
        RenderingInfo(mode="hybrid", framework="Next.js"),
    )
    assert rec.strategy == "stealth-headers"


def test_fetch_error_recommends_do_not_scrape():
    rec = build(
        _http(error="ConnectError: refused"),
        RobotsInfo(fetched=False, url=""),
        AntiBotInfo(),
        RenderingInfo(mode="unknown"),
    )
    assert rec.strategy == "do-not-scrape"
