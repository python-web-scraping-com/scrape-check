# scrape-check

[![CI](https://github.com/python-web-scraping-com/scrape-check/actions/workflows/ci.yml/badge.svg)](https://github.com/python-web-scraping-com/scrape-check/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> Profile any URL for scrapability — before you write a single line of scraper code.

`scrape-check` is a small CLI that tells you what you'll be up against if you try
to scrape a website. It makes two HTTP requests (one to `/robots.txt`, one to
your target) and reports:

- **`robots.txt`** — is your path allowed? What `Crawl-delay` applies? Where are the sitemaps?
- **Anti-bot stack** — Cloudflare, Akamai Bot Manager, DataDome, HUMAN (PerimeterX),
  Imperva/Incapsula, Kasada, Queue-it, AWS WAF, F5 BIG-IP, Sucuri, reCAPTCHA,
  hCaptcha, Turnstile — detected from headers, cookies, and body signatures.
  Informational CDNs/hosts (Cloudflare, Akamai, Fastly, CloudFront, Vercel,
  Netlify, Section.io, StackPath) are reported separately so they don't skew the
  recommendation.
- **Rendering mode** — server-rendered, client-rendered, or hybrid? Which framework
  (Next.js, Nuxt, Gatsby, SvelteKit, Remix, Astro, React, Vue, Angular)?
- **HTTP basics** — status, redirects, HTTP version, rate-limit headers, `Retry-After`.
- **A recommendation** — `requests` is fine / use stealth headers / needs a headless
  browser / don't scrape.

It does **not** execute JavaScript, solve challenges, or attempt to bypass anything —
this is a planning tool, not a scraper.

## Install

`scrape-check` is not on PyPI yet — install it from source, straight from GitHub:

```bash
pip install git+https://github.com/python-web-scraping-com/scrape-check.git
```

Since it's a command-line tool, [`pipx`](https://pipx.pypa.io) is a good way to install it in its own isolated environment:

```bash
pipx install git+https://github.com/python-web-scraping-com/scrape-check.git
```

Requires Python 3.9+.

## Usage

```bash
scrape-check example.com
scrape-check https://news.ycombinator.com
scrape-check https://www.zillow.com --json
scrape-check https://example.com --user-agent "MyBot/1.0"
scrape-check https://example.com --timeout 30
```

### Batch mode

Profile a whole list of URLs at once. Pass a file with one URL per line
(blank lines and `#` comments are ignored), or pipe URLs in on stdin with `-`:

```bash
scrape-check --batch urls.txt
cat urls.txt | scrape-check -
```

Batch mode prints a compact one-row-per-URL summary (strategy, status, anti-bot,
rendering) and, with `--json`, a JSON array of full reports. URLs are analyzed
concurrently with a bounded worker pool; tune it with `--concurrency` and add a
`--delay` between requests to stay polite:

```bash
scrape-check --batch urls.txt --concurrency 4 --delay 0.5
scrape-check --batch urls.txt --json > report.json
```

The exit code reflects the recommendation, which is useful in CI. In batch mode
it's the **worst** recommendation across every URL:

| Strategy          | Exit code |
| ----------------- | --------- |
| `requests`        | `0`       |
| `stealth-headers` | `1`       |
| `headless`        | `1`       |
| `do-not-scrape`   | `2`       |

### Options

| Flag                | Description                                                         |
| ------------------- | ----------------------------------------------------------------- |
| `--batch FILE`      | Read URLs (one per line) from a file; `-` reads from stdin.        |
| `--concurrency N`   | Max URLs analyzed in parallel in batch mode (default `8`).         |
| `--delay SECONDS`   | Politeness pause between requests in batch mode (default `0`).     |
| `--timeout SECONDS` | Per-request HTTP timeout (default `15`).                           |
| `--user-agent`, `-u`| Override the User-Agent used when fetching the target.             |
| `--json`            | Emit a machine-readable JSON report (an array in batch mode).      |

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

Batch mode prints a table like:

```
                          scrape-check — batch summary
 URL                        strategy         status  anti-bot            rendering
 https://example.com/       requests         200     —                   ssr
 https://shop.example/      headless         403     DataDome            hybrid
 https://app.example/       headless         200     —                   csr
```

## Use as a library

```python
from scrape_check import analyze, analyze_batch

report = analyze("https://example.com")
print(report.recommendation.strategy)   # "requests"
print(report.antibot.detected)          # []
print(report.rendering.mode)            # "ssr"
print(report.robots.sitemaps)           # ["https://example.com/sitemap.xml"]

# Profile many URLs concurrently (bounded worker pool, results in input order):
reports = analyze_batch(
    ["https://example.com", "https://news.ycombinator.com"],
    concurrency=4,
)
for r in reports:
    print(r.target, r.recommendation.strategy)
```

`analyze()` returns a dataclass `Report`; call `report.to_dict()` to serialize.
`analyze_batch()` returns a `list[Report]` in the same order as the URLs you pass.

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
- ⚙️ [Scaling & Deploying Python Scrapers](https://python-web-scraping.com/scaling-python-web-scrapers/) — Scrapy, async crawling with asyncio/HTTPX, concurrency control, and storing scraped data at scale.
- ⚡ [Async scraping with asyncio & HTTPX](https://python-web-scraping.com/scaling-python-web-scrapers/asynchronous-scraping-with-asyncio-and-httpx/) — how to fan out a URL list concurrently once `scrape-check --batch` tells you which ones are safe.

## Development

```bash
git clone https://github.com/python-web-scraping-com/scrape-check.git
cd scrape-check
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
