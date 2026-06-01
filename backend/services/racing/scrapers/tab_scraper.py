from __future__ import annotations

from backend.core.config import settings
from backend.services.racing.scrapers.base_scraper import BaseRacingScraper, ScrapeConfig


class TabScraper(BaseRacingScraper):
    source_name = "tab"

    def __init__(self, start_url: str | None = None, use_playwright: bool = False):
        # LEGAL / COMPLIANCE WARNING: Check TAB robots.txt and terms of use
        # before enabling this scraper, especially for commercial usage. Prefer
        # official licensed APIs if available.
        super().__init__(
            ScrapeConfig(
                source_name=self.source_name,
                start_url=start_url if start_url is not None else settings.TAB_SCRAPE_URL,
                use_playwright=use_playwright,
            )
        )

    # TODO: Replace the generic JSON-LD/table parser with source-specific,
    # permission-approved selectors once real sample pages and terms are reviewed.
    # Source-specific selector notes to implement after permission review:
    # - Meeting cards: inspect TAB race meeting containers for track names and race links.
    # - Race time/name: map each race card header to ScrapedRace.start_time/name.
    # - Runners: map runner rows to horse name, barrier/draw, jockey, trainer, weight and scratchings.
    # - Odds: map fixed-win market price cells to ScrapedOdds and preserve movement fields if present.
