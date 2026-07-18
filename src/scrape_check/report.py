from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from scrape_check.models import Report

_STRATEGY_STYLE = {
    "requests": ("green", "Safe to use plain HTTP (requests / httpx)"),
    "stealth-headers": ("yellow", "Plain HTTP may work — use realistic headers"),
    "headless": ("magenta", "Use a headless browser (Playwright / Selenium)"),
    "do-not-scrape": ("red", "Do not scrape"),
}


_STRATEGY_COLOR = {
    "requests": "green",
    "stealth-headers": "yellow",
    "headless": "magenta",
    "do-not-scrape": "red",
}


def render_batch(reports: list[Report], console: Console) -> None:
    """Render a compact one-row-per-URL summary table for a batch run."""
    t = Table(title="scrape-check — batch summary", expand=True)
    t.add_column("URL", overflow="fold")
    t.add_column("strategy", no_wrap=True)
    t.add_column("status", justify="right", no_wrap=True)
    t.add_column("anti-bot", overflow="fold")
    t.add_column("rendering", no_wrap=True)

    for report in reports:
        strategy = report.recommendation.strategy
        style = _STRATEGY_COLOR.get(strategy, "white")

        h = report.http
        if h.error:
            status_cell = Text("err", style="red")
        else:
            status_style = (
                "green" if 200 <= h.status < 400 else "yellow" if h.status < 500 else "red"
            )
            status_cell = Text(str(h.status), style=status_style)

        a = report.antibot
        if a.bot_defense:
            antibot_cell = Text(", ".join(a.bot_defense), style="red")
        elif a.cdns:
            antibot_cell = Text(", ".join(a.cdns), style="yellow")
        else:
            antibot_cell = Text("—", style="dim")

        t.add_row(
            report.target,
            Text(strategy, style=f"bold {style}"),
            status_cell,
            antibot_cell,
            Text(report.rendering.mode, style=_rendering_style(report.rendering.mode)),
        )

    console.print()
    console.print(t)
    console.print()


def render(report: Report, console: Console) -> None:
    console.print()
    console.print(_summary_panel(report))
    console.print(_http_table(report))
    console.print(_robots_table(report))
    console.print(_antibot_panel(report))
    console.print(_rendering_panel(report))
    console.print(_recommendation_panel(report))
    console.print()


def _summary_panel(report: Report) -> Panel:
    target = Text(report.target, style="bold cyan")
    if report.http.final_url != report.target and report.http.final_url:
        target.append(f"\n→ {report.http.final_url}", style="dim")
    return Panel(target, title="scrape-check", border_style="cyan")


def _http_table(report: Report) -> Table:
    t = Table(title="HTTP", show_header=False, expand=True)
    t.add_column(style="bold", no_wrap=True)
    t.add_column()
    h = report.http
    if h.error:
        t.add_row("error", Text(h.error, style="red"))
        return t
    status_style = "green" if 200 <= h.status < 400 else "yellow" if h.status < 500 else "red"
    t.add_row("status", Text(f"{h.status}", style=status_style))
    t.add_row("http version", h.http_version or "?")
    t.add_row("server", h.server or "—")
    t.add_row("content-type", h.content_type or "—")
    if h.content_length is not None:
        t.add_row("content-length", f"{h.content_length:,} bytes")
    t.add_row("elapsed", f"{h.elapsed_ms} ms")
    if h.redirects:
        t.add_row("redirects", "\n".join(h.redirects))
    if h.retry_after:
        t.add_row("retry-after", h.retry_after)
    if h.rate_limit_headers:
        rl = "\n".join(f"{k}: {v}" for k, v in h.rate_limit_headers.items())
        t.add_row("rate-limit", rl)
    return t


def _robots_table(report: Report) -> Table:
    t = Table(title="robots.txt", show_header=False, expand=True)
    t.add_column(style="bold", no_wrap=True)
    t.add_column()
    r = report.robots
    t.add_row("url", r.url or "—")
    if r.error:
        t.add_row("error", Text(r.error, style="yellow"))
        return t
    t.add_row("status", str(r.status) if r.status else "—")
    if r.allowed is True:
        t.add_row("allowed", Text("yes", style="green"))
    elif r.allowed is False:
        t.add_row("allowed", Text("no — disallowed for your path", style="red"))
    else:
        t.add_row("allowed", "—")
    if r.crawl_delay is not None:
        t.add_row("crawl-delay", f"{r.crawl_delay}s")
    if r.sitemaps:
        t.add_row("sitemaps", "\n".join(r.sitemaps[:5]) + ("\n…" if len(r.sitemaps) > 5 else ""))
    return t


def _antibot_panel(report: Report) -> Panel:
    a = report.antibot
    if not a.detected and not a.challenge_page:
        body: Group | Text = Text("no anti-bot signals detected", style="green")
    else:
        rows: list[Text] = []
        if a.challenge_page:
            rows.append(Text("⚠ response looks like a challenge page", style="bold red"))
        for product in a.bot_defense:
            ev_text = Text()
            ev_text.append(product, style="bold red")
            for e in a.signals.get(product, []):
                ev_text.append(f"\n  • {e}", style="dim")
            rows.append(ev_text)
        for product in a.cdns:
            ev_text = Text()
            ev_text.append(product, style="bold yellow")
            ev_text.append("  (informational)", style="dim italic")
            for e in a.signals.get(product, []):
                ev_text.append(f"\n  • {e}", style="dim")
            rows.append(ev_text)
        body = Group(*rows)
    return Panel(body, title="Anti-bot", border_style="magenta")


def _rendering_panel(report: Report) -> Panel:
    r = report.rendering
    body = Text()
    body.append(f"mode: ", style="bold")
    body.append(r.mode, style=_rendering_style(r.mode))
    if r.framework:
        body.append(f"  •  framework: ", style="bold")
        body.append(r.framework)
    for s in r.signals:
        body.append(f"\n  • {s}", style="dim")
    return Panel(body, title="Rendering", border_style="blue")


def _rendering_style(mode: str) -> str:
    return {
        "ssr": "green",
        "hybrid": "yellow",
        "csr": "magenta",
    }.get(mode, "dim")


def _recommendation_panel(report: Report) -> Panel:
    rec = report.recommendation
    style, summary = _STRATEGY_STYLE.get(rec.strategy, ("white", rec.strategy))
    body = Text()
    body.append(rec.strategy, style=f"bold {style}")
    body.append(f"  —  {summary}\n")
    for reason in rec.reasons:
        body.append(f"\n  • {reason}", style="dim")
    if rec.notes:
        body.append("\n")
        for note in rec.notes:
            body.append(f"\n  → {note}", style="dim italic")
    return Panel(body, title="Recommendation", border_style=style)
