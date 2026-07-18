from __future__ import annotations

import json
import sys
from urllib.parse import urlparse

import click
from rich.console import Console

from scrape_check import __version__
from scrape_check.analyze import analyze
from scrape_check.batch import analyze_batch, exit_code_for, parse_url_lines, worst_exit_code
from scrape_check.report import render, render_batch


def _normalize_url(raw: str) -> str:
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc:
        raise click.BadParameter(f"could not parse URL: {raw!r}")
    return raw


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="scrape-check")
@click.argument("url", required=False)
@click.option(
    "--batch",
    "batch_file",
    type=click.File("r"),
    default=None,
    help="Read URLs (one per line) from a file and profile them all. Use '-' for stdin.",
)
@click.option(
    "--concurrency",
    type=int,
    default=8,
    show_default=True,
    help="Maximum URLs to analyze in parallel in batch mode.",
)
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
    "--delay",
    type=float,
    default=0.0,
    show_default=True,
    help="Politeness pause (seconds) between requests in batch mode. Be a good citizen.",
)
@click.option(
    "--user-agent",
    "-u",
    default=None,
    help="Override the User-Agent used when fetching the target.",
)
def main(
    url: str | None,
    batch_file,
    concurrency: int,
    as_json: bool,
    timeout: float,
    delay: float,
    user_agent: str | None,
) -> None:
    """Profile a URL (or many) for scrapability.

    Inspects robots.txt, anti-bot signals, rendering mode, and suggests a
    scraping strategy. Makes one request to /robots.txt and one to the
    target URL — no JavaScript is executed.

    Examples:

      scrape-check https://example.com

      scrape-check example.com --json

      scrape-check --batch urls.txt

      cat urls.txt | scrape-check -
    """
    # Batch mode: --batch FILE, or the special URL "-" meaning read from stdin.
    if batch_file is not None or url == "-":
        source = batch_file if batch_file is not None else sys.stdin
        _run_batch(source, concurrency, as_json, timeout, delay, user_agent)
        return

    if not url:
        raise click.UsageError("Provide a URL, or use --batch FILE (or '-' to read URLs from stdin).")

    target = _normalize_url(url)
    report = analyze(target, timeout=timeout, user_agent=user_agent)

    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2, default=str))
        sys.exit(exit_code_for(report.recommendation.strategy))

    console = Console()
    render(report, console)
    sys.exit(exit_code_for(report.recommendation.strategy))


def _run_batch(source, concurrency: int, as_json: bool, timeout: float, delay: float, user_agent) -> None:
    raw_urls = parse_url_lines(source)
    if not raw_urls:
        raise click.UsageError("no URLs found — provide a non-empty list via --batch FILE or stdin.")

    targets = [_normalize_url(u) for u in raw_urls]
    reports = analyze_batch(
        targets,
        timeout=timeout,
        user_agent=user_agent,
        concurrency=concurrency,
        delay=delay,
    )

    if as_json:
        click.echo(json.dumps([r.to_dict() for r in reports], indent=2, default=str))
    else:
        render_batch(reports, Console())

    sys.exit(worst_exit_code(reports))


if __name__ == "__main__":
    main()
