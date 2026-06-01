from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, time as datetime_time, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from backend.core.config import settings

logger = logging.getLogger(__name__)

# LEGAL / COMPLIANCE WARNING:
# Before enabling any scraper commercially, check each website's robots.txt,
# terms of use, licensing restrictions, and applicable law. Prefer official APIs
# whenever possible. The scraper layer exists to normalize publicly available data
# only when you have permission to collect it.


class ScraperUnavailableError(RuntimeError):
    pass


@dataclass
class ScrapeConfig:
    source_name: str
    start_url: str | None
    rate_limit_seconds: float = settings.SCRAPING_RATE_LIMIT_SECONDS
    timeout_seconds: float = settings.SCRAPING_HTTP_TIMEOUT_SECONDS
    user_agent: str = settings.SCRAPING_USER_AGENT
    use_playwright: bool = False


@dataclass
class ScrapedRunner:
    external_id: str | None = None
    horse_name: str | None = None
    barrier: int | None = None
    jockey: str | None = None
    trainer: str | None = None
    weight_kg: Decimal | None = None
    scratched: bool = False
    past_form: list[Any] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapedOdds:
    runner_external_id: str | None = None
    horse_name: str | None = None
    bookmaker: str | None = None
    market_type: str = "win"
    odds_decimal: Decimal | None = None
    market_movement: dict[str, Any] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapedResult:
    runner_external_id: str | None = None
    horse_name: str | None = None
    position: int | None = None
    margin: Decimal | None = None
    starting_price: Decimal | None = None
    result_status: str = "official"
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapedRace:
    external_id: str | None = None
    race_number: int | None = None
    name: str | None = None
    start_time: datetime | None = None
    distance_meters: int | None = None
    race_class: str | None = None
    status: str = "scheduled"
    track_condition: str | None = None
    runners: list[ScrapedRunner] = field(default_factory=list)
    odds: list[ScrapedOdds] = field(default_factory=list)
    results: list[ScrapedResult] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapedMeeting:
    external_id: str | None = None
    meeting_date: date | None = None
    track_name: str | None = None
    country: str | None = None
    state: str | None = None
    track_condition: str | None = None
    weather: str | None = None
    races: list[ScrapedRace] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapeDiagnostics:
    http_status_code: int | None = None
    page_title: str | None = None
    tables_found: int = 0
    json_ld_found: int = 0
    meetings_parsed: int = 0
    races_parsed: int = 0
    runners_parsed: int = 0
    odds_parsed: int = 0
    zero_records_reason: str | None = None
    used_playwright: bool = False


@dataclass
class ScrapeResult:
    source_name: str
    status: str
    meetings: list[ScrapedMeeting] = field(default_factory=list)
    error_message: str | None = None
    missing_data_fields: list[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    diagnostics: ScrapeDiagnostics = field(default_factory=ScrapeDiagnostics)


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def stable_id(*parts: Any) -> str:
    joined = ":".join(normalize_name(str(part)) for part in parts if part not in (None, ""))
    return re.sub(r"\s+", "-", joined)[:160] or "unknown"


def parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("$", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except Exception:
        return None


def parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def parse_time_for_date(value: Any, race_date: date) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%H:%M", "%I:%M%p", "%I:%M %p"):
        try:
            parsed_time = datetime.strptime(text.upper().replace(" ", ""), fmt.replace(" ", "")).time()
            return datetime.combine(race_date, parsed_time, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class BaseRacingScraper:
    source_name = "base"

    def __init__(self, config: ScrapeConfig):
        self.config = config
        self._last_request_monotonic = 0.0
        self._last_http_status_code: int | None = None
        self._last_used_playwright = False

    def scrape(self, race_date: date) -> ScrapeResult:
        if not self.config.start_url:
            diagnostics = ScrapeDiagnostics(zero_records_reason="scraper URL is not configured")
            return ScrapeResult(
                source_name=self.source_name,
                status="unavailable",
                error_message="Data source unavailable: scraper URL is not configured.",
                diagnostics=diagnostics,
            )
        try:
            html = self.fetch_page(self.build_url(race_date))
            if self._looks_blocked_or_empty(html):
                if not self.config.use_playwright:
                    logger.info("%s returned empty/blocked HTML; retrying with Playwright", self.source_name)
                    html = self.fetch_page_with_playwright(self.build_url(race_date))
                if self._looks_blocked_or_empty(html):
                    diagnostics = self.build_diagnostics(html, [])
                    diagnostics.zero_records_reason = "blocked or empty page after browser fetch"
                    return ScrapeResult(
                        self.source_name,
                        "unavailable",
                        error_message="Data source unavailable: blocked or empty page.",
                        diagnostics=diagnostics,
                    )
            meetings = self.parse(html, race_date)
            diagnostics = self.build_diagnostics(html, meetings)
            missing = self.collect_missing_fields(meetings)
            if not meetings:
                diagnostics.zero_records_reason = diagnostics.zero_records_reason or "no parseable meetings found"
                missing = sorted(set([*missing, "meetings"]))
            status = "completed_with_warnings" if missing else "completed"
            logger.info(
                "Scraping succeeded for %s: http_status=%s title=%r tables=%s json_ld=%s meetings=%s races=%s runners=%s odds=%s missing=%s zero_reason=%s",
                self.source_name, diagnostics.http_status_code, diagnostics.page_title, diagnostics.tables_found,
                diagnostics.json_ld_found, diagnostics.meetings_parsed, diagnostics.races_parsed, diagnostics.runners_parsed,
                diagnostics.odds_parsed, missing, diagnostics.zero_records_reason,
            )
            return ScrapeResult(self.source_name, status, meetings, missing_data_fields=missing, diagnostics=diagnostics)
        except httpx.HTTPStatusError as exc:
            return self._http_error_result(exc)
        except httpx.TimeoutException as exc:
            logger.warning("Scraping timed out for %s: %s", self.source_name, exc)
            return ScrapeResult(
                self.source_name,
                "failed",
                error_message=f"Data source timeout: {exc}",
                diagnostics=ScrapeDiagnostics(http_status_code=self._last_http_status_code, zero_records_reason="timeout"),
            )
        except PlaywrightTimeoutError as exc:
            logger.warning("Browser scraping timed out for %s: %s", self.source_name, exc)
            return ScrapeResult(
                self.source_name,
                "failed",
                error_message=f"Browser data source timeout: {exc}",
                diagnostics=ScrapeDiagnostics(http_status_code=self._last_http_status_code, used_playwright=True, zero_records_reason="browser timeout"),
            )
        except PlaywrightError as exc:
            logger.warning("Browser scraping unavailable for %s: %s", self.source_name, exc)
            message = str(exc)
            if "Executable doesn't exist" in message or "playwright install" in message:
                message = "Browser fetch unavailable: Playwright browser is not installed. Run `python -m playwright install chromium`."
            return ScrapeResult(
                self.source_name,
                "unavailable",
                error_message=message,
                diagnostics=ScrapeDiagnostics(
                    http_status_code=self._last_http_status_code,
                    used_playwright=True,
                    zero_records_reason="browser fetch unavailable",
                ),
            )
        except Exception as exc:
            logger.exception("Scraping failed for %s", self.source_name)
            return ScrapeResult(
                self.source_name,
                "failed",
                error_message=str(exc),
                diagnostics=ScrapeDiagnostics(
                    http_status_code=self._last_http_status_code,
                    used_playwright=self._last_used_playwright,
                    zero_records_reason="unexpected scraper error",
                ),
            )

    def build_url(self, race_date: date) -> str:
        assert self.config.start_url is not None
        return self.config.start_url.format(date=race_date.isoformat())

    def fetch_page(self, url: str) -> str:
        elapsed = time.monotonic() - self._last_request_monotonic
        if elapsed < self.config.rate_limit_seconds:
            time.sleep(self.config.rate_limit_seconds - elapsed)
        self._last_request_monotonic = time.monotonic()
        if self.config.use_playwright:
            return self.fetch_page_with_playwright(url)
        self._last_used_playwright = False
        headers = {"User-Agent": self.config.user_agent}
        with httpx.Client(timeout=self.config.timeout_seconds, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            self._last_http_status_code = response.status_code
            logger.info("Scraper %s fetched %s with HTTP %s", self.source_name, url, response.status_code)
            response.raise_for_status()
            return response.text

    def fetch_page_with_playwright(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ScraperUnavailableError("Playwright is not installed. Install Playwright browsers before JS-rendered scraping.") from exc
        self._last_used_playwright = True
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(user_agent=self.config.user_agent)
            response = page.goto(url, wait_until="networkidle", timeout=int(self.config.timeout_seconds * 1000))
            self._last_http_status_code = response.status if response else None
            logger.info("Browser scraper %s fetched %s with HTTP %s", self.source_name, url, self._last_http_status_code)
            html = page.content()
            browser.close()
            return html

    def _http_error_result(self, exc: httpx.HTTPStatusError) -> ScrapeResult:
        status_code = exc.response.status_code
        if status_code == 403:
            reason = "blocked by source (403 Forbidden)"
            status = "unavailable"
        elif status_code == 404:
            reason = "source page not found (404)"
            status = "unavailable"
        else:
            reason = f"HTTP error {status_code}"
            status = "failed"
        logger.warning("Scraping failed for %s: %s", self.source_name, reason)
        return ScrapeResult(
            self.source_name,
            status,
            error_message=f"Data source unavailable: {reason} for url '{exc.request.url}'",
            diagnostics=ScrapeDiagnostics(http_status_code=status_code, zero_records_reason=reason, used_playwright=self._last_used_playwright),
        )

    def _looks_blocked_or_empty(self, html: str) -> bool:
        text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True).lower()
        if len(text) < 40:
            return True
        blocked_terms = ("access denied", "forbidden", "captcha", "enable javascript", "just a moment", "blocked")
        return any(term in text for term in blocked_terms)

    def build_diagnostics(self, html: str, meetings: list[ScrapedMeeting]) -> ScrapeDiagnostics:
        soup = BeautifulSoup(html or "", "html.parser")
        title = soup.find("title") or soup.find("h1")
        races = [race for meeting in meetings for race in meeting.races]
        runners = [runner for race in races for runner in race.runners]
        odds = [odds for race in races for odds in race.odds]
        diagnostics = ScrapeDiagnostics(
            http_status_code=self._last_http_status_code,
            page_title=title.get_text(" ", strip=True) if title else None,
            tables_found=len(soup.find_all("table")),
            json_ld_found=len(soup.find_all("script", type="application/ld+json")),
            meetings_parsed=len(meetings),
            races_parsed=len(races),
            runners_parsed=len(runners),
            odds_parsed=len(odds),
            used_playwright=self._last_used_playwright,
        )
        if not meetings:
            if diagnostics.tables_found == 0 and diagnostics.json_ld_found == 0:
                diagnostics.zero_records_reason = "no JSON-LD or tables found"
            elif diagnostics.tables_found > 0:
                diagnostics.zero_records_reason = "tables found but no runner rows matched expected headings"
            else:
                diagnostics.zero_records_reason = "JSON-LD found but no racing meeting fields matched"
        return diagnostics

    def parse(self, html: str, race_date: date) -> list[ScrapedMeeting]:
        soup = BeautifulSoup(html, "html.parser")
        json_meetings = self.parse_json_ld(soup, race_date)
        if json_meetings:
            return json_meetings
        return self.parse_tables(soup, race_date)

    def parse_json_ld(self, soup: BeautifulSoup, race_date: date) -> list[ScrapedMeeting]:
        meetings: list[ScrapedMeeting] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                payload = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if not name:
                    continue
                meeting = ScrapedMeeting(
                    external_id=stable_id(self.source_name, race_date, name),
                    meeting_date=race_date,
                    track_name=name,
                    raw_payload={"source_type": "json_ld", "payload": item},
                )
                meetings.append(meeting)
        return meetings

    def _extract_headers(self, table: Any) -> list[str]:
        header_row = table.select_one("thead tr")
        if header_row is None:
            header_row = next((row for row in table.find_all("tr") if row.find("th") is not None), None)
        if header_row is None:
            return []
        return [normalize_name(cell.get_text(" ", strip=True)) for cell in header_row.find_all(["th", "td"])]

    def parse_tables(self, soup: BeautifulSoup, race_date: date) -> list[ScrapedMeeting]:
        # Generic fallback for pages with simple HTML tables. Provider-specific
        # adapters should override this once real, permitted source payloads are known.
        title = soup.find("h1") or soup.find("title")
        track_name = title.get_text(" ", strip=True) if title else self.source_name.title()
        meeting = ScrapedMeeting(
            external_id=stable_id(self.source_name, race_date, track_name),
            meeting_date=race_date,
            track_name=track_name,
            raw_payload={"source_type": "html_table_fallback"},
        )
        for index, table in enumerate(soup.find_all("table"), start=1):
            headers = self._extract_headers(table)
            if not headers:
                continue
            race = ScrapedRace(
                external_id=stable_id(meeting.external_id, "race", index),
                race_number=index,
                name=f"Race {index}",
                start_time=datetime.combine(race_date, datetime_time.min, tzinfo=timezone.utc),
                raw_payload={"headers": headers},
            )
            for row in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                if len(cells) < 2 or self._is_header_row(row, headers, cells):
                    continue
                mapped = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
                horse_name = self._field(mapped, "runner", "horse", "name", "selection")
                if not horse_name:
                    continue
                runner = ScrapedRunner(
                    external_id=stable_id(race.external_id, horse_name),
                    horse_name=horse_name,
                    barrier=parse_int(self._field(mapped, "barrier", "draw")),
                    jockey=self._field(mapped, "jockey"),
                    trainer=self._field(mapped, "trainer"),
                    weight_kg=parse_decimal(self._field(mapped, "weight", "weight kg")),
                    scratched="scr" in " ".join(cells).lower(),
                    raw_payload=mapped,
                )
                race.runners.append(runner)
                odds = parse_decimal(self._field(mapped, "odds", "fixed", "price"))
                if odds:
                    race.odds.append(
                        ScrapedOdds(
                            runner_external_id=runner.external_id,
                            horse_name=horse_name,
                            bookmaker=self.source_name,
                            odds_decimal=odds,
                            raw_payload=mapped,
                        )
                    )
            if race.runners or race.odds:
                meeting.races.append(race)
        return [meeting] if meeting.races else []

    def _is_header_row(self, row: Any, headers: list[str], cells: list[str]) -> bool:
        if row.find("th") is not None:
            return True
        normalized_cells = [normalize_name(cell) for cell in cells]
        normalized_cells = [cell for cell in normalized_cells if cell]
        if normalized_cells == headers[: len(normalized_cells)]:
            return True
        header_terms = {"runner", "horse", "name", "selection"}
        first_cell = normalized_cells[0] if normalized_cells else ""
        return first_cell in header_terms and any(cell in {"barrier", "draw", "jockey", "trainer", "weight", "odds", "fixed odds", "price"} for cell in normalized_cells[1:])

    def _field(self, mapped: dict[str, str], *names: str) -> str | None:
        normalized = {normalize_name(key): value for key, value in mapped.items()}
        for name in names:
            wanted = normalize_name(name)
            for key, value in normalized.items():
                if wanted == key or wanted in key:
                    return value
        return None

    def collect_missing_fields(self, meetings: list[ScrapedMeeting]) -> list[str]:
        missing: set[str] = set()
        if not meetings:
            missing.add("meetings")
        for meeting in meetings:
            if not meeting.track_name:
                missing.add("meeting.track_name")
            if not meeting.meeting_date:
                missing.add("meeting.meeting_date")
            if not meeting.races:
                missing.add("meeting.races")
            for race in meeting.races:
                if not race.name:
                    missing.add("race.name")
                if not race.start_time:
                    missing.add("race.start_time")
                if not race.runners:
                    missing.add("race.runners")
                for runner in race.runners:
                    if not runner.horse_name:
                        missing.add("runner.horse_name")
                    if runner.barrier is None:
                        missing.add("runner.barrier")
                    if runner.weight_kg is None:
                        missing.add("runner.weight_kg")
                    if not runner.jockey:
                        missing.add("runner.jockey")
                    if not runner.trainer:
                        missing.add("runner.trainer")
        return sorted(missing)
