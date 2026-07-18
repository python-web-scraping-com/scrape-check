import httpx
import respx

from scrape_check.batch import (
    analyze_batch,
    exit_code_for,
    parse_url_lines,
    worst_exit_code,
)
from scrape_check.models import AntiBotInfo, HttpInfo, Recommendation, RenderingInfo, Report, RobotsInfo


def _report(strategy: str) -> Report:
    return Report(
        target="https://example.com/",
        http=HttpInfo(
            url="https://example.com/",
            final_url="https://example.com/",
            status=200,
            http_version="HTTP/1.1",
            server="nginx",
            content_type="text/html",
            content_length=100,
            elapsed_ms=1,
        ),
        robots=RobotsInfo(fetched=True, url="https://example.com/robots.txt", allowed=True),
        antibot=AntiBotInfo(),
        rendering=RenderingInfo(mode="ssr"),
        recommendation=Recommendation(strategy=strategy),
    )


def test_parse_url_lines_skips_blanks_and_comments():
    lines = [
        "https://a.com",
        "",
        "   ",
        "# a comment",
        "https://b.com  # inline note",
        "b.com/path",
    ]
    assert parse_url_lines(lines) == ["https://a.com", "https://b.com", "b.com/path"]


def test_exit_code_mapping():
    assert exit_code_for("requests") == 0
    assert exit_code_for("stealth-headers") == 1
    assert exit_code_for("headless") == 1
    assert exit_code_for("do-not-scrape") == 2
    assert exit_code_for("unknown-thing") == 0


def test_worst_exit_code_is_the_max():
    reports = [_report("requests"), _report("do-not-scrape"), _report("stealth-headers")]
    assert worst_exit_code(reports) == 2


def test_worst_exit_code_empty_batch():
    assert worst_exit_code([]) == 0


def _mock_host(host: str, *, body: str, headers=None):
    respx.get(f"https://{host}/robots.txt").mock(return_value=httpx.Response(404))
    respx.get(f"https://{host}/").mock(
        return_value=httpx.Response(200, html=body, headers=headers or {})
    )


_SSR_BODY = "<!doctype html><html><head><title>Plain HTML Page Title Here</title></head><body>" + (
    "<p>Real article content that is server rendered.</p>" * 20
) + "</body></html>"


@respx.mock
def test_analyze_batch_preserves_order():
    _mock_host("a.com", body=_SSR_BODY)
    _mock_host("b.com", body=_SSR_BODY)
    _mock_host("c.com", body=_SSR_BODY)

    urls = ["https://a.com/", "https://b.com/", "https://c.com/"]
    reports = analyze_batch(urls, concurrency=3)

    assert [r.target for r in reports] == urls


@respx.mock
def test_analyze_batch_mixed_recommendations():
    # a.com: clean SSR -> requests
    _mock_host("a.com", body=_SSR_BODY)
    # b.com: active bot defense (DataDome cookie) -> headless
    respx.get("https://b.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://b.com/").mock(
        return_value=httpx.Response(200, html=_SSR_BODY, headers={"set-cookie": "datadome=xyz"})
    )

    reports = analyze_batch(["https://a.com/", "https://b.com/"], concurrency=2)
    strategies = {r.target: r.recommendation.strategy for r in reports}

    assert strategies["https://a.com/"] == "requests"
    assert strategies["https://b.com/"] == "headless"
    assert worst_exit_code(reports) == 1


@respx.mock
def test_analyze_batch_respects_concurrency_of_one():
    _mock_host("a.com", body=_SSR_BODY)
    _mock_host("b.com", body=_SSR_BODY)

    reports = analyze_batch(["https://a.com/", "https://b.com/"], concurrency=1)
    assert len(reports) == 2


def test_analyze_batch_empty_returns_empty():
    assert analyze_batch([]) == []
