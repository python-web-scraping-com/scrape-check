"""Batch analysis: profile many URLs concurrently with a bounded worker pool.

Each URL is analysed by the same synchronous :func:`scrape_check.analyze.analyze`
used for single-URL runs, so batch and single mode always agree. Concurrency is
capped by a thread pool (``analyze`` is I/O-bound on httpx), and results are
returned in the original input order regardless of completion order.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from scrape_check.analyze import analyze
from scrape_check.models import Report

# Exit code per recommendation strategy — 0 green, 1 yellow, 2 red. The batch
# exit code is the worst (highest) across every URL analysed.
STRATEGY_EXIT_CODES = {
    "requests": 0,
    "stealth-headers": 1,
    "headless": 1,
    "do-not-scrape": 2,
}


def exit_code_for(strategy: str) -> int:
    """Map a recommendation strategy to its process exit code."""
    return STRATEGY_EXIT_CODES.get(strategy, 0)


def worst_exit_code(reports: Iterable[Report]) -> int:
    """Return the highest (worst) exit code across a batch of reports."""
    codes = [exit_code_for(r.recommendation.strategy) for r in reports]
    return max(codes) if codes else 0


def parse_url_lines(lines: Iterable[str]) -> list[str]:
    """Extract URLs from an iterable of raw lines.

    Blank lines and ``#`` comments are ignored, and inline trailing comments are
    stripped so annotated URL lists (``https://site  # notes``) work.
    """
    urls: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Strip an inline comment while leaving the URL intact.
        if " #" in line:
            line = line.split(" #", 1)[0].strip()
        if line:
            urls.append(line)
    return urls


def analyze_batch(
    urls: list[str],
    *,
    timeout: float = 15.0,
    user_agent: str | None = None,
    concurrency: int = 8,
    delay: float = 0.0,
) -> list[Report]:
    """Analyse many URLs concurrently, preserving input order.

    Args:
        urls: Normalised target URLs.
        timeout: Per-request HTTP timeout in seconds.
        user_agent: Optional User-Agent override for the target fetch.
        concurrency: Maximum number of URLs analysed in parallel (>= 1).
        delay: Politeness pause, in seconds, inserted between task submissions.
            Spaces out the load a batch puts on shared infrastructure; ``0``
            disables it.

    Returns:
        One :class:`~scrape_check.models.Report` per input URL, in order.
    """
    if not urls:
        return []

    workers = max(1, min(concurrency, len(urls)))

    def _run(target: str) -> Report:
        return analyze(target, timeout=timeout, user_agent=user_agent)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        for i, target in enumerate(urls):
            if delay > 0 and i > 0:
                time.sleep(delay)
            futures.append(pool.submit(_run, target))
        # future.result() preserves submission order, so the output list matches
        # the input order even though tasks finish out of order.
        return [f.result() for f in futures]
