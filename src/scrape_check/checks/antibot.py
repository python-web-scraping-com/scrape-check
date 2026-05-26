from __future__ import annotations

from scrape_check.fetch import FetchResult
from scrape_check.models import AntiBotInfo

# CDNs may run bot management or may not — flagging them alone shouldn't change
# the recommendation. Only the bot-defense entries do that.
_CDN_PRODUCTS = {
    "Cloudflare (CDN)",
    "Akamai (CDN)",
    "Fastly",
    "AWS CloudFront",
    "Sucuri (CDN)",
    "Imperva (CDN)",
}


def _add(signals: dict[str, list[str]], product: str, evidence: str) -> None:
    signals.setdefault(product, []).append(evidence)


def detect(result: FetchResult) -> AntiBotInfo:
    signals: dict[str, list[str]] = {}
    headers = {k.lower(): v for k, v in result.headers.items()}
    cookies = {c.lower() for c in result.cookies.keys()}
    body_lc = result.text.lower() if result.text else ""

    # --- Cloudflare ---
    cf_cdn = False
    cf_bot = False
    if "cf-ray" in headers:
        _add(signals, "Cloudflare (CDN)", f"cf-ray: {headers['cf-ray']}")
        cf_cdn = True
    if headers.get("server", "").lower().startswith("cloudflare"):
        _add(signals, "Cloudflare (CDN)", f"server: {headers['server']}")
        cf_cdn = True
    if "cf-cache-status" in headers:
        _add(signals, "Cloudflare (CDN)", f"cf-cache-status: {headers['cf-cache-status']}")
        cf_cdn = True
    if "cf-mitigated" in headers:
        _add(signals, "Cloudflare Bot Management", f"cf-mitigated: {headers['cf-mitigated']}")
        cf_bot = True
    if any(c.startswith("cf_clearance") for c in cookies):
        _add(signals, "Cloudflare Bot Management", "cf_clearance cookie set (challenge passed)")
        cf_bot = True
    if any(c.startswith("__cf_bm") for c in cookies):
        _add(signals, "Cloudflare Bot Management", "__cf_bm cookie set")
        cf_bot = True

    # --- Akamai ---
    if "akamai" in headers.get("server", "").lower():
        _add(signals, "Akamai (CDN)", f"server: {headers['server']}")
    if any(h.startswith("x-akamai") for h in headers):
        _add(signals, "Akamai (CDN)", "x-akamai-* header present")
    if any(c.startswith("ak_bmsc") or c.startswith("bm_sv") or c.startswith("_abck") for c in cookies):
        _add(signals, "Akamai Bot Manager", "bot-manager cookie set")

    # --- DataDome ---
    if "x-dd-b" in headers or "x-datadome" in headers:
        _add(signals, "DataDome", "x-dd-* header present")
    if "datadome" in cookies:
        _add(signals, "DataDome", "datadome cookie set")
    if "datadome" in body_lc and ("captcha" in body_lc or "challenge" in body_lc):
        _add(signals, "DataDome", "challenge marker in body")

    # --- PerimeterX / HUMAN ---
    if any(c.startswith("_px") for c in cookies):
        _add(signals, "HUMAN (PerimeterX)", "_px* cookie set")
    if any(h.startswith("x-px") for h in headers):
        _add(signals, "HUMAN (PerimeterX)", "x-px-* header present")

    # --- Imperva / Incapsula ---
    if "x-iinfo" in headers:
        _add(signals, "Imperva (CDN)", "x-iinfo header present")
    if "imperva" in headers.get("x-cdn", "").lower():
        _add(signals, "Imperva (CDN)", f"x-cdn: {headers['x-cdn']}")
    if any(c.startswith("incap_ses") or c.startswith("visid_incap") for c in cookies):
        _add(signals, "Imperva (Incapsula)", "incap cookie set")

    # --- Sucuri ---
    if "sucuri" in headers.get("server", "").lower():
        _add(signals, "Sucuri (CDN)", f"server: {headers['server']}")
    if "x-sucuri-id" in headers:
        _add(signals, "Sucuri (CDN)", "x-sucuri-id header present")
    if "x-sucuri-block" in headers:
        _add(signals, "Sucuri WAF", f"x-sucuri-block: {headers['x-sucuri-block']}")

    # --- F5 BIG-IP ---
    if any(c.startswith("bigipserver") or c.startswith("ts01") for c in cookies):
        _add(signals, "F5 BIG-IP", "BIG-IP cookie set")

    # --- Fastly ---
    if "x-served-by" in headers and "cache-" in headers["x-served-by"].lower():
        _add(signals, "Fastly", f"x-served-by: {headers['x-served-by']}")
    if "fastly" in headers.get("server", "").lower():
        _add(signals, "Fastly", f"server: {headers['server']}")

    # --- AWS CloudFront ---
    if "cloudfront" in headers.get("server", "").lower() or "x-amz-cf-id" in headers:
        _add(signals, "AWS CloudFront", "cloudfront header present")

    # --- Captcha widgets in body — strong scraper-blocker signal ---
    if "g-recaptcha" in body_lc or "recaptcha/api.js" in body_lc:
        _add(signals, "reCAPTCHA", "widget present in HTML")
    if "h-captcha" in body_lc or "hcaptcha.com/1/api.js" in body_lc:
        _add(signals, "hCaptcha", "widget present in HTML")
    if "challenges.cloudflare.com/turnstile" in body_lc:
        _add(signals, "Cloudflare Turnstile", "widget present in HTML")

    # --- Challenge page heuristics ---
    challenge_page = False
    if result.status in (403, 429, 503):
        if cf_cdn and (
            "just a moment" in body_lc
            or "checking your browser" in body_lc
            or "enable javascript and cookies" in body_lc
        ):
            challenge_page = True
            _add(signals, "Cloudflare Bot Management", "interstitial page text")
        if "datadome" in signals or "DataDome" in signals or "HUMAN (PerimeterX)" in signals:
            challenge_page = True
    if "pardon our interruption" in body_lc:  # PerimeterX classic interstitial
        challenge_page = True
        _add(signals, "HUMAN (PerimeterX)", "interstitial page text")

    cdns = sorted(p for p in signals if p in _CDN_PRODUCTS)
    bot_defense = sorted(p for p in signals if p not in _CDN_PRODUCTS)

    return AntiBotInfo(
        cdns=cdns,
        bot_defense=bot_defense,
        signals=signals,
        challenge_page=challenge_page,
    )
