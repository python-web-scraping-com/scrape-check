from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class HttpInfo:
    url: str
    final_url: str
    status: int
    http_version: str
    server: str | None
    content_type: str | None
    content_length: int | None
    elapsed_ms: int
    redirects: list[str] = field(default_factory=list)
    rate_limit_headers: dict[str, str] = field(default_factory=dict)
    retry_after: str | None = None
    error: str | None = None


@dataclass
class RobotsInfo:
    fetched: bool
    url: str
    status: int | None = None
    allowed: bool | None = None
    matched_rule: str | None = None
    crawl_delay: float | None = None
    sitemaps: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class AntiBotInfo:
    # CDNs / infrastructure — informational only.
    cdns: list[str] = field(default_factory=list)
    # Active bot-defense products — what actually drives the recommendation.
    bot_defense: list[str] = field(default_factory=list)
    # Per-product evidence, covers both categories.
    signals: dict[str, list[str]] = field(default_factory=dict)
    challenge_page: bool = False

    @property
    def detected(self) -> list[str]:
        return sorted(set(self.cdns) | set(self.bot_defense))


@dataclass
class RenderingInfo:
    mode: str  # "ssr", "csr", "hybrid", "unknown"
    framework: str | None = None
    signals: list[str] = field(default_factory=list)
    text_ratio: float | None = None


@dataclass
class Recommendation:
    strategy: str  # "requests", "stealth-headers", "headless", "do-not-scrape"
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Report:
    target: str
    http: HttpInfo
    robots: RobotsInfo
    antibot: AntiBotInfo
    rendering: RenderingInfo
    recommendation: Recommendation

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
