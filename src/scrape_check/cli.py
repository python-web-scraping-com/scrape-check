from __future__ import annotations

import json
import sys
from urllib.parse import urlparse

import click
from rich.console import Console

from scrape_check import __version__
from scrape_check.analyze import analyze
from scrape_check.report import render


def _normalize_url(raw: str) -> str:
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc:
        raise click.BadParameter(f"could not parse URL: {raw!r}")
    return raw


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="scrape-check")
@click.argument("url")
@click.option(
    "--json", "as_json", is_flag=True, help="Emit a machine-readable JSON report instead of rich text."
)
@click.option(
    "--timeout",
    type=float,
    default=15.0,
    show_default=True,
    help="HTTP timeout in seconds (per request).",
)
@click.option(
    "--user-agent",
    "-u",
    default=None,
    help="Override the User-Agent used when fetching the target.",
)
def main(url: str, as_json: bool, timeout: float, user_agent: str | None) -> None:
    """Profile a URL for scrapability.

    Inspects robots.txt, anti-bot signals, rendering mode, and suggests a
    scraping strategy. Makes one request to /robots.txt and one to the
    target URL — no JavaScript is executed.

    Examples:

      scrape-check https://example.com

      scrape-check example.com --json
    """
    target = _normalize_url(url)
    report = analyze(target, timeout=timeout, user_agent=user_agent)

    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2, default=str))
        return

    console = Console()
    render(report, console)
    sys.exit(_exit_code(report.recommendation.strategy))


def _exit_code(strategy: str) -> int:
    # 0: green light, 1: yellow, 2: red. Useful for CI / scripting.
    return {
        "requests": 0,
        "stealth-headers": 1,
        "headless": 1,
        "do-not-scrape": 2,
    }.get(strategy, 0)


if __name__ == "__main__":
    main()
