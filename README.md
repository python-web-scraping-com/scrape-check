# scrape-check

> Profile any URL for scrapability — before you write a single line of scraper code.

`scrape-check` is a small CLI that tells you what you'll be up against if you try
to scrape a website. It makes two HTTP requests (one to `/robots.txt`, one to
your target) and reports:

- **`robots.txt`** — is your path allowed? What `Crawl-delay` applies? Where are the sitemaps?
- **Anti-bot stack** — Cloudflare, Akamai Bot Manager, DataDome, HUMAN (PerimeterX),
  Imperva, Sucuri, Fastly, reCAPTCHA, hCaptcha, Turnstile — detected from headers,
  cookies, and body signatures.
- **Rendering mode** — server-rendered, client-rendered, or hybrid? Which framework
  (Next.js, Nuxt, Gatsby, SvelteKit, Remix, Astro, React, Vue, Angular)?
- **HTTP basics** — status, redirects, HTTP version, rate-limit headers, `Retry-After`.
- **A recommendation** — `requests` is fine / use stealth headers / needs a headless
  browser / don't scrape.

It does **not** execute JavaScript, solve challenges, or attempt to bypass anything —
this is a planning tool, not a scraper.

## Install

From source:

```bash
pip install git+https://github.com/python-web-scraping-com/scrape-check.git
```

Requires Python 3.9+.

## Usage

```bash
scrape-check example.com
scrape-check https://news.ycombinator.com
scrape-check https://www.zillow.com --json
scrape-check https://example.com --user-agent "MyBot/1.0"
```

The exit code reflects the recommendation, which is useful in CI:

| Strategy          | Exit code |
| ----------------- | --------- |
| `requests`        | `0`       |
| `stealth-headers` | `1`       |
| `headless`        | `1`       |
| `do-not-scrape`   | `2`       |

## Example

```
╭─ scrape-check ──────────────────────────────────────────────╮
│ https://example.com                                         │
╰─────────────────────────────────────────────────────────────╯

                              HTTP
 status          200
 http version    HTTP/1.1
 server          nginx
 elapsed         142 ms

                          robots.txt
 url        https://example.com/robots.txt
 status     200
 allowed    yes
 sitemaps   https://example.com/sitemap.xml

╭─ Anti-bot ──────────────────────────────────────────────────╮
│ no anti-bot signals detected                                │
╰─────────────────────────────────────────────────────────────╯
╭─ Rendering ─────────────────────────────────────────────────╮
│ mode: ssr                                                   │
│   • visible-text ratio: 21.4%                               │
╰─────────────────────────────────────────────────────────────╯
╭─ Recommendation ────────────────────────────────────────────╮
│ requests — Safe to use plain HTTP (requests / httpx)        │
│                                                             │
│   • server-rendered HTML, no anti-bot signals detected      │
╰─────────────────────────────────────────────────────────────╯
```

## Use as a library

```python
from scrape_check import analyze

report = analyze("https://example.com")
print(report.recommendation.strategy)   # "requests"
print(report.antibot.detected)          # []
print(report.rendering.mode)            # "ssr"
print(report.robots.sitemaps)           # ["https://example.com/sitemap.xml"]
```

`analyze()` returns a dataclass `Report`; call `report.to_dict()` to serialize.

## What it can't tell you

- `scrape-check` only loads the initial HTML. Sites that gate content behind
  scroll, click, or login will look fine here but block real scraping.
- Anti-bot products are detected from *signatures*. A missing detection doesn't
  mean a site has no protection — it might just be dormant for unauthenticated
  requests.
- Rendering classification is a heuristic. When in doubt, run with `--json` and
  inspect the `rendering.signals` field.

## Going deeper

Once `scrape-check` tells you what you're dealing with, the
[python-web-scraping.com](https://python-web-scraping.com) guides cover what to do next:

- 🔰 [Complete Guide to Python Web Scraping](https://python-web-scraping.com/the-complete-guide-to-python-web-scraping/) — the fundamentals you'll need for `requests`-friendly sites.
- 🛡 [Advanced Scraping & Anti-bot Evasion](https://python-web-scraping.com/advanced-scraping-techniques-anti-bot-evasion/) — headless browsers, stealth patching, proxy rotation, and getting past Cloudflare / Akamai.
- ⚖️ [Legal, Ethical & Compliance](https://python-web-scraping.com/legal-ethical-compliance-in-web-scraping/) — `robots.txt`, GDPR, copyright, and the responsible scraping playbook.

## Development

```bash
git clone https://github.com/python-web-scraping-com/scrape-check.git
cd scrape-check
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
