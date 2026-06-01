from __future__ import annotations

import re
from datetime import date, datetime, time as datetime_time, timezone
from typing import Any

from bs4 import BeautifulSoup

from backend.core.config import settings
from backend.services.racing.scrapers.base_scraper import (
    BaseRacingScraper,
    ScrapeConfig,
    ScrapedMeeting,
    ScrapedOdds,
    ScrapedRace,
    ScrapedResult,
    ScrapedRunner,
    normalize_name,
    parse_decimal,
    parse_int,
    parse_time_for_date,
    stable_id,
)


class PuntersScraper(BaseRacingScraper):
    source_name = "punters"
    default_url = "https://www.punters.com.au/form-guide/"

    def __init__(self, start_url: str | None = None, use_playwright: bool = True):
        # LEGAL / COMPLIANCE WARNING: Check Punters robots.txt and terms of use
        # before enabling this scraper, especially for commercial usage. Prefer
        # official licensed APIs if available.
        super().__init__(
            ScrapeConfig(
                source_name=self.source_name,
                start_url=start_url if start_url is not None else (settings.PUNTERS_SCRAPE_URL or self.default_url),
                use_playwright=use_playwright,
            )
        )

    # Source-specific selector notes to implement/adjust after permission review:
    # - Meeting: h1/h2 headings on form-guide pages, e.g. "Rosehill Gardens Races"
    #   and "Rosehill Gardens, NSW".
    # - Race cards: links/sections whose href/text contains `/race-<number>/`,
    #   plus table blocks with headings like "Runner Details".
    # - Runners: tables with columns such as Runner Details, Quick Form, Odds,
    #   or rows/cards containing data labels for Barrier/Draw, Jockey, Trainer, Weight.
    # - Results: result tables/cards containing Position/Pos/Place and SP/Starting Price.
    # - Odds: fixed odds are read from Odds/Price/SP columns when present.

    def parse(self, html: str, race_date: date) -> list[ScrapedMeeting]:
        soup = BeautifulSoup(html, "html.parser")
        if self._is_access_denied(soup):
            return []
        meeting = self._parse_meeting_shell(soup, race_date)
        races = self._parse_race_tables(soup, race_date, meeting.external_id or stable_id(self.source_name, race_date, meeting.track_name))
        if not races:
            races = self._parse_race_links(soup, race_date, meeting.external_id or stable_id(self.source_name, race_date, meeting.track_name))
        meeting.races = races
        return [meeting] if meeting.races else []

    def _is_access_denied(self, soup: BeautifulSoup) -> bool:
        text = soup.get_text(" ", strip=True).lower()
        return "access denied" in text or "request was blocked" in text or "403 error" in text

    def _parse_meeting_shell(self, soup: BeautifulSoup, race_date: date) -> ScrapedMeeting:
        heading = soup.select_one("h1")
        subheading = soup.select_one("h2")
        title_text = heading.get_text(" ", strip=True) if heading else (soup.title.get_text(" ", strip=True) if soup.title else "Punters")
        track_name = re.sub(r"\s+Races$", "", title_text).strip()
        if subheading:
            subheading_text = subheading.get_text(" ", strip=True)
            if subheading_text and "form guide" not in subheading_text.lower():
                track_name = re.sub(r",\s*[A-Z]{2,3}$", "", subheading_text).strip() or track_name
        return ScrapedMeeting(
            external_id=stable_id(self.source_name, race_date, track_name),
            meeting_date=race_date,
            track_name=track_name,
            raw_payload={"source_type": "punters_form_page", "selectors": {"meeting": "h1, h2"}},
        )

    def _parse_race_links(self, soup: BeautifulSoup, race_date: date, meeting_id: str) -> list[ScrapedRace]:
        races: list[ScrapedRace] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="race-"]'):
            text = link.get_text(" ", strip=True)
            href = link.get("href") or ""
            race_number = self._race_number(text) or self._race_number(href)
            if not race_number:
                continue
            name = self._race_name_from_text(text, race_number) or f"Race {race_number}"
            key = stable_id(meeting_id, race_number, name)
            if key in seen:
                continue
            seen.add(key)
            races.append(
                ScrapedRace(
                    external_id=key,
                    race_number=race_number,
                    name=name,
                    start_time=parse_time_for_date(text, race_date) or datetime.combine(race_date, datetime_time.min, tzinfo=timezone.utc),
                    raw_payload={"source_type": "punters_race_link", "text": text, "href": href, "selector": 'a[href*="race-"]'},
                )
            )
        return races

    def _parse_race_tables(self, soup: BeautifulSoup, race_date: date, meeting_id: str) -> list[ScrapedRace]:
        races: list[ScrapedRace] = []
        for index, table in enumerate(soup.select("table"), start=1):
            headers = self._extract_headers(table)
            if not headers or not self._looks_like_punters_runner_table(headers):
                continue
            context = self._table_context_text(table)
            race_number = self._race_number(context) or index
            race_name = self._race_name_from_text(context, race_number) or f"Race {race_number}"
            race = ScrapedRace(
                external_id=stable_id(meeting_id, race_number, race_name),
                race_number=race_number,
                name=race_name,
                start_time=parse_time_for_date(context, race_date) or datetime.combine(race_date, datetime_time.min, tzinfo=timezone.utc),
                raw_payload={"source_type": "punters_runner_table", "headers": headers, "selector": "table"},
            )
            for row in table.select("tbody tr") or table.select("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                if len(cells) < 2 or self._is_header_row(row, headers, cells):
                    continue
                mapped = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
                runner = self._runner_from_row(mapped, race.external_id)
                result = self._result_from_row(mapped, runner)
                odds = self._odds_from_row(mapped, runner)
                if runner.horse_name:
                    race.runners.append(runner)
                if odds.odds_decimal is not None:
                    race.odds.append(odds)
                if result.position is not None:
                    race.results.append(result)
            if race.runners or race.results:
                races.append(race)
        return races

    def _looks_like_punters_runner_table(self, headers: list[str]) -> bool:
        joined = " ".join(headers)
        return any(term in joined for term in ("runner", "horse", "name", "runner details")) and any(
            term in joined for term in ("odds", "price", "quick form", "barrier", "draw", "jockey", "trainer", "weight", "pos", "position")
        )

    def _table_context_text(self, table: Any) -> str:
        headings = []
        for sibling in table.find_all_previous(["h1", "h2", "h3", "h4", "a"], limit=8):
            text = sibling.get_text(" ", strip=True)
            if text:
                headings.append(text)
        for text in headings:
            if self._race_number(text):
                return text
        return " ".join(reversed(headings))

    def _runner_from_row(self, mapped: dict[str, str], race_id: str) -> ScrapedRunner:
        horse_name = self._field(mapped, "runner details", "runner", "horse", "name", "selection")
        # Punters indexed snippets sometimes put quick-form strings in Runner Details.
        if horse_name and re.fullmatch(r"[0-9xX-]+", horse_name.replace(" ", "")):
            horse_name = None
        return ScrapedRunner(
            external_id=stable_id(race_id, horse_name) if horse_name else None,
            horse_name=horse_name,
            barrier=parse_int(self._field(mapped, "barrier", "draw")),
            jockey=self._field(mapped, "jockey"),
            trainer=self._field(mapped, "trainer"),
            weight_kg=parse_decimal(self._field(mapped, "weight", "weight kg", "kg")),
            scratched="scr" in " ".join(mapped.values()).lower(),
            past_form=self._past_form(self._field(mapped, "quick form", "form")),
            raw_payload={"selector": "table tbody tr", **mapped},
        )

    def _odds_from_row(self, mapped: dict[str, str], runner: ScrapedRunner) -> ScrapedOdds:
        odds_value = parse_decimal(self._field(mapped, "odds", "price", "fixed", "sp", "starting price"))
        return ScrapedOdds(
            runner_external_id=runner.external_id,
            horse_name=runner.horse_name,
            bookmaker=self.source_name,
            odds_decimal=odds_value,
            raw_payload={"selector": "odds/price/sp column", **mapped},
        )

    def _result_from_row(self, mapped: dict[str, str], runner: ScrapedRunner) -> ScrapedResult:
        return ScrapedResult(
            runner_external_id=runner.external_id,
            horse_name=runner.horse_name,
            position=parse_int(self._field(mapped, "position", "pos", "place", "result")),
            starting_price=parse_decimal(self._field(mapped, "sp", "starting price", "odds", "price")),
            raw_payload={"selector": "position/pos/place column", **mapped},
        )

    def _past_form(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [char for char in value if char.isdigit() or char.lower() == "x"][:10]

    def _race_number(self, value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"(?:race|r)\s*(\d+)", value, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _race_name_from_text(self, value: str | None, race_number: int | None) -> str | None:
        if not value:
            return None
        text = re.sub(r"\s+", " ", value).strip()
        if race_number:
            text = re.sub(rf"\b(?:R|Race)\s*{race_number}\b", "", text, flags=re.IGNORECASE).strip(" -|")
        text = re.sub(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", "", text, flags=re.IGNORECASE).strip(" -|")
        return text or None
