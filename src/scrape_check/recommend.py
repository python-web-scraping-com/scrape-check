from __future__ import annotations

from scrape_check.models import AntiBotInfo, HttpInfo, Recommendation, RenderingInfo, RobotsInfo

# Captcha widgets count as blocking even when no full bot-defense product fires.
_CAPTCHA_PRODUCTS = {"reCAPTCHA", "hCaptcha", "Cloudflare Turnstile"}


def build(
    http: HttpInfo,
    robots: RobotsInfo,
    antibot: AntiBotInfo,
    rendering: RenderingInfo,
) -> Recommendation:
    reasons: list[str] = []
    notes: list[str] = []

    if http.error:
        return Recommendation(
            strategy="do-not-scrape",
            reasons=[f"could not reach target: {http.error}"],
        )

    # 4xx/5xx without a challenge page usually means UA/IP blocking or rate
    # limiting — the response we got isn't representative of the real content.
    blocked_status = http.status in (401, 403, 405, 406, 429, 451) or 500 <= http.status < 600

    # robots.txt rules are advisory, not legally binding everywhere, but a
    # confirmed disallow makes the polite default "do not scrape".
    if robots.allowed is False:
        reasons.append(f"robots.txt disallows this path (rule: {robots.matched_rule or 'Disallow'})")
        notes.append("see https://python-web-scraping.com/legal-ethical-compliance-in-web-scraping/")
        return Recommendation(strategy="do-not-scrape", reasons=reasons, notes=notes)

    if antibot.challenge_page:
        reasons.append("response looks like an anti-bot challenge page")
        return Recommendation(
            strategy="headless",
            reasons=reasons,
            notes=["see https://python-web-scraping.com/advanced-scraping-techniques-anti-bot-evasion/"],
        )

    blocking = list(antibot.bot_defense)
    captchas = sorted(set(antibot.bot_defense) & _CAPTCHA_PRODUCTS)
    if blocking:
        reasons.append(f"active bot defense: {', '.join(blocking)}")
    elif antibot.cdns:
        notes.append(
            f"behind a CDN ({', '.join(antibot.cdns)}) but no active bot-defense signals — "
            "expect rate limiting, not hard blocks"
        )

    if rendering.mode == "csr":
        reasons.append(f"content is client-rendered ({rendering.framework or 'unknown framework'})")
        notes.append("you'll need a headless browser to get the rendered HTML")

    needs_browser = bool(blocking) or rendering.mode == "csr" or bool(captchas)
    if needs_browser:
        strategy = "headless"
    elif blocked_status:
        reasons.append(
            f"server returned HTTP {http.status} — request was likely blocked, "
            "real content may need different headers or a browser"
        )
        strategy = "stealth-headers"
    elif rendering.mode == "hybrid":
        notes.append(
            "initial HTML likely contains hydration data — check for __NEXT_DATA__ / __NUXT__ before reaching for a browser"
        )
        strategy = "stealth-headers"
    elif antibot.cdns:
        strategy = "stealth-headers"
        reasons.append("CDN may rate-limit obviously-bot User-Agents")
    else:
        strategy = "requests"
        reasons.append("server-rendered HTML, no anti-bot signals detected")

    if robots.crawl_delay:
        notes.append(f"robots.txt requests Crawl-delay: {robots.crawl_delay}s")
    if http.retry_after:
        notes.append(f"server returned Retry-After: {http.retry_after}")
    if http.rate_limit_headers:
        notes.append(f"rate-limit headers present: {', '.join(http.rate_limit_headers)}")

    if strategy != "requests":
        notes.append("see https://python-web-scraping.com/advanced-scraping-techniques-anti-bot-evasion/")

    return Recommendation(strategy=strategy, reasons=reasons, notes=notes)
