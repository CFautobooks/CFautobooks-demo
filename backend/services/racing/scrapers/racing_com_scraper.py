from __future__ import annotations

from backend.core.config import settings
from backend.services.racing.scrapers.base_scraper import BaseRacingScraper, ScrapeConfig


class RacingComScraper(BaseRacingScraper):
    source_name = "racing_com"

    def __init__(self, start_url: str | None = None, use_playwright: bool = False):
        # LEGAL / COMPLIANCE WARNING: Check Racing.com robots.txt and terms of use
        # before enabling this scraper, especially for commercial usage. Prefer
        # official licensed APIs if available.
        super().__init__(
            ScrapeConfig(
                source_name=self.source_name,
                start_url=start_url if start_url is not None else settings.RACING_COM_SCRAPE_URL,
                use_playwright=use_playwright,
            )
        )

    # TODO: Replace the generic JSON-LD/table parser with source-specific,
    # permission-approved selectors once real sample pages and terms are reviewed.
