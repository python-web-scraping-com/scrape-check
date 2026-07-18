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


def test_kasada_header_and_cookie():
    info = antibot.detect(
        _result(headers={"x-kpsdk-ct": "abc"}, cookies={"KP_UIDz": "xyz"})
    )
    assert "Kasada" in info.bot_defense


def test_queueit_cookie():
    info = antibot.detect(_result(cookies={"QueueITAccepted-SDFrts345E3d": "x"}))
    assert "Queue-it" in info.bot_defense


def test_queueit_body_reference():
    info = antibot.detect(
        _result(text="<html><body>redirecting to queue-it.net waiting room</body></html>")
    )
    assert "Queue-it" in info.bot_defense


def test_aws_waf_token_cookie():
    info = antibot.detect(_result(cookies={"aws-waf-token": "xyz"}))
    assert "AWS WAF" in info.bot_defense


def test_imperva_incapsula_nlbi_cookie():
    info = antibot.detect(_result(cookies={"nlbi_12345": "x"}))
    assert "Imperva (Incapsula)" in info.bot_defense


def test_f5_bigip_server_cookie():
    info = antibot.detect(_result(cookies={"BIGipServerpool_web": "abc"}))
    assert "F5 BIG-IP" in info.bot_defense


def test_f5_ts_cookie():
    info = antibot.detect(_result(cookies={"TS01a2b3c4": "value"}))
    assert "F5 BIG-IP" in info.bot_defense


def test_ordinary_ts_prefixed_cookie_is_not_f5():
    # A cookie merely starting with "ts" (e.g. "tsettings") must not trip F5.
    info = antibot.detect(_result(cookies={"tsettings": "1"}))
    assert "F5 BIG-IP" not in info.bot_defense


def test_vercel_is_informational_cdn():
    info = antibot.detect(_result(headers={"x-vercel-id": "iad1::abc", "server": "Vercel"}))
    assert "Vercel" in info.cdns
    assert info.bot_defense == []


def test_netlify_is_informational_cdn():
    info = antibot.detect(_result(headers={"x-nf-request-id": "abc", "server": "Netlify"}))
    assert "Netlify" in info.cdns
    assert info.bot_defense == []


def test_section_io_via_header():
    info = antibot.detect(_result(headers={"via": "1.1 varnish (section.io)"}))
    assert "Section.io" in info.cdns


def test_stackpath_hw_header():
    info = antibot.detect(_result(headers={"x-hw": "1234.dop003"}))
    assert "StackPath" in info.cdns
