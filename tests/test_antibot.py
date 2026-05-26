import httpx

from scrape_check.checks import antibot
from scrape_check.fetch import FetchResult


def _result(*, headers=None, cookies=None, text="", status=200):
    h = httpx.Headers(headers or {})
    cookie_jar = httpx.Cookies()
    for k, v in (cookies or {}).items():
        cookie_jar.set(k, v, domain="example.com")
    return FetchResult(
        request_url="https://example.com/",
        final_url="https://example.com/",
        status=status,
        http_version="HTTP/1.1",
        headers=h,
        cookies=cookie_jar,
        text=text,
        elapsed_ms=10,
        redirects=[],
    )


def test_cloudflare_cdn_alone_is_not_bot_defense():
    info = antibot.detect(_result(headers={"cf-ray": "abc-DFW", "server": "cloudflare"}))
    assert "Cloudflare (CDN)" in info.cdns
    assert info.bot_defense == []
    assert info.challenge_page is False


def test_cf_bm_cookie_indicates_active_bot_management():
    info = antibot.detect(_result(headers={"cf-ray": "abc"}, cookies={"__cf_bm": "x"}))
    assert "Cloudflare (CDN)" in info.cdns
    assert "Cloudflare Bot Management" in info.bot_defense


def test_cloudflare_challenge_page():
    info = antibot.detect(
        _result(
            status=503,
            headers={"server": "cloudflare", "cf-ray": "abc"},
            text="<html><body>Just a moment... checking your browser</body></html>",
        )
    )
    assert info.challenge_page is True
    assert "Cloudflare Bot Management" in info.bot_defense


def test_datadome_cookie():
    info = antibot.detect(_result(cookies={"datadome": "xyz"}))
    assert "DataDome" in info.bot_defense


def test_akamai_bot_manager_cookie():
    info = antibot.detect(_result(cookies={"_abck": "xyz"}))
    assert "Akamai Bot Manager" in info.bot_defense


def test_clean_response_has_no_signals():
    info = antibot.detect(_result(headers={"server": "nginx"}, text="<html><body>hello</body></html>"))
    assert info.detected == []
    assert info.challenge_page is False


def test_recaptcha_widget_is_bot_defense():
    info = antibot.detect(
        _result(text='<html><script src="https://www.google.com/recaptcha/api.js"></script></html>')
    )
    assert "reCAPTCHA" in info.bot_defense


def test_detected_property_combines_both_lists():
    info = antibot.detect(
        _result(headers={"cf-ray": "abc"}, cookies={"datadome": "x"})
    )
    assert "Cloudflare (CDN)" in info.detected
    assert "DataDome" in info.detected
