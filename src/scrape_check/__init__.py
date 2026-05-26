"""scrape-check — profile any URL for scrapability."""

from scrape_check.analyze import analyze
from scrape_check.models import (
    AntiBotInfo,
    HttpInfo,
    Recommendation,
    RenderingInfo,
    Report,
    RobotsInfo,
)

__version__ = "0.1.0"

__all__ = [
    "analyze",
    "AntiBotInfo",
    "HttpInfo",
    "Recommendation",
    "RenderingInfo",
    "Report",
    "RobotsInfo",
    "__version__",
]
