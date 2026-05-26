import httpx

from scrape_check.checks import rendering
from scrape_check.fetch import FetchResult


def _result(text: str) -> FetchResult:
    return FetchResult(
        request_url="https://example.com/",
        final_url="https://example.com/",
        status=200,
        http_version="HTTP/1.1",
        headers=httpx.Headers({}),
        cookies=httpx.Cookies(),
        text=text,
        elapsed_ms=10,
        redirects=[],
    )


_DOCTYPE_HEAD = (
    "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>Test Page Title For Realistic Header Length</title>"
    "</head>"
)


def test_ssr_plain_html():
    html = _DOCTYPE_HEAD + "<body>" + "<p>Article paragraph with real content.</p>" * 30 + "</body></html>"
    info = rendering.analyze(_result(html))
    assert info.mode == "ssr"
    assert info.framework is None


def test_csr_empty_react_root():
    html = (
        _DOCTYPE_HEAD
        + "<body><div id='root'></div>"
        + "<script src='/static/react.bundle.js'></script>"
        + "<script src='/static/app.bundle.js'></script>"
        + "</body></html>"
    )
    info = rendering.analyze(_result(html))
    assert info.mode == "csr"


def test_next_js_detected_as_hybrid():
    html = (
        _DOCTYPE_HEAD
        + "<body><div id='__next'>"
        + "<p>Server-rendered Next.js page with real article body content.</p>" * 5
        + "</div>"
        + "<script id='__NEXT_DATA__' type='application/json'>{\"props\":{}}</script>"
        + "<script src='/_next/static/chunks/main.js'></script>"
        + "</body></html>"
    )
    info = rendering.analyze(_result(html))
    assert info.mode == "hybrid"
    assert info.framework == "Next.js"


def test_too_small_body_is_unknown():
    info = rendering.analyze(_result("<html></html>"))
    assert info.mode == "unknown"
