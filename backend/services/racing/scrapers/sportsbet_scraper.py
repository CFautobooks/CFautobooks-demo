from __future__ import annotations

from backend.core.config import settings
from backend.services.racing.scrapers.base_scraper import BaseRacingScraper, ScrapeConfig


class SportsbetScraper(BaseRacingScraper):
    source_name = "sportsbet"

    def __init__(self, start_url: str | None = None, use_playwright: bool = False):
        # LEGAL / COMPLIANCE WARNING: Check Sportsbet robots.txt and terms of use
        # before enabling this scraper, especially for commercial usage. Prefer
        # official licensed APIs if available.
        super().__init__(
            ScrapeConfig(
                source_name=self.source_name,
                start_url=start_url if start_url is not None else settings.SPORTSBET_SCRAPE_URL,
                use_playwright=use_playwright,
            )
        )

    # TODO: Replace the generic JSON-LD/table parser with source-specific,
    # permission-approved selectors once real sample pages and terms are reviewed.
    # Source-specific selector notes to implement after permission review:
    # - Sportsbet is commonly JS-rendered/blocked; enable use_playwright when permitted.
    # - Meeting/race containers: identify event-list cards and racing market sections.
    # - Runners: extract selection names and scratching state from market rows.
    # - Odds: extract fixed win odds and any previous-price movement indicators.
