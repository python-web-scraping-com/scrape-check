"""scrape-check — profile any URL for scrapability."""

from scrape_check.analyze import analyze
from scrape_check.batch import analyze_batch
from scrape_check.models import (
    AntiBotInfo,
    HttpInfo,
    Recommendation,
    RenderingInfo,
    Report,
    RobotsInfo,
)

__version__ = "0.2.0"

__all__ = [
    "analyze",
    "analyze_batch",
    "AntiBotInfo",
    "HttpInfo",
    "Recommendation",
    "RenderingInfo",
    "Report",
    "RobotsInfo",
    "__version__",
]
