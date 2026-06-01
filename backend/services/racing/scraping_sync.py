from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.models.racing import Jockey, Meeting, OddsSnapshot, Race, Result, Runner, SyncRun, Trainer
from backend.services.racing.scrapers import PuntersScraper, RacingComScraper, SportsbetScraper, TabScraper
from backend.services.racing.scrapers.base_scraper import (
    BaseRacingScraper,
    ScrapeResult,
    ScrapedMeeting,
    ScrapedOdds,
    ScrapedRace,
    ScrapedResult,
    ScrapedRunner,
    normalize_name,
    stable_id,
)
from backend.services.racing.sync import calculate_and_store_model_ratings

logger = logging.getLogger(__name__)
WEB_DATA_SOURCE = "web_sourced"


def _diagnostics_payload(scrape_result: ScrapeResult) -> dict[str, Any]:
    diagnostics = scrape_result.diagnostics
    return {
        "http_status_code": diagnostics.http_status_code,
        "page_title": diagnostics.page_title,
        "tables_found": diagnostics.tables_found,
        "json_ld_found": diagnostics.json_ld_found,
        "meetings_parsed": diagnostics.meetings_parsed,
        "races_parsed": diagnostics.races_parsed,
        "runners_parsed": diagnostics.runners_parsed,
        "odds_parsed": diagnostics.odds_parsed,
        "zero_records_reason": diagnostics.zero_records_reason,
        "used_playwright": diagnostics.used_playwright,
    }


def _attach_scrape_diagnostics(run: SyncRun, scrape_result: ScrapeResult) -> None:
    metadata = dict(run.metadata_json or {})
    metadata["scrape_diagnostics"] = _diagnostics_payload(scrape_result)
    run.metadata_json = metadata


def available_scrapers() -> dict[str, type[BaseRacingScraper]]:
    return {
        "tab": TabScraper,
        "sportsbet": SportsbetScraper,
        "racing_com": RacingComScraper,
        "punters": PuntersScraper,
    }


def configured_scrapers(source: str = "all") -> list[BaseRacingScraper]:
    registry = available_scrapers()
    if source != "all":
        if source not in registry:
            raise ValueError(f"Unknown scraper source '{source}'")
        return [registry[source]()]
    return [scraper_cls() for scraper_cls in registry.values()]


def _start_scrape_run(db: Session, source: str, race_date: date) -> SyncRun:
    run = SyncRun(
        provider=f"web:{source}",
        data_source=WEB_DATA_SOURCE,
        sync_type="scraping",
        status="running",
        metadata_json={"date": race_date.isoformat(), "source": source, "label": "web-sourced data"},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _finish_run(
    db: Session,
    run: SyncRun,
    status: str,
    records: int,
    missing: list[str] | None = None,
    error: str | None = None,
) -> SyncRun:
    run.status = status
    run.completed_at = datetime.now(timezone.utc)
    run.records_processed = records
    run.missing_data_fields = sorted(set(missing or []))
    run.error_message = error
    db.commit()
    db.refresh(run)
    if status.startswith("completed"):
        logger.info("Scraping sync succeeded provider=%s records=%s missing=%s", run.provider, records, run.missing_data_fields)
    else:
        logger.warning("Scraping sync failed provider=%s error=%s", run.provider, error)
    return run


def _quality(required: dict[str, Any]) -> tuple[str, list[str]]:
    missing = [key for key, value in required.items() if value in (None, "", [])]
    return ("insufficient data" if missing else "sufficient", missing)


def _get_or_create_person(db: Session, model: type[Jockey] | type[Trainer], provider: str, name: str | None) -> Jockey | Trainer | None:
    if not name:
        return None
    external_id = stable_id(provider, name)
    person = db.query(model).filter(model.provider == provider, model.external_id == external_id).one_or_none()
    if not person:
        person = model(provider=provider, data_source=WEB_DATA_SOURCE, external_id=external_id, name=name, raw_payload={"source": provider})
        db.add(person)
        db.flush()
    else:
        person.name = name
        person.data_source = WEB_DATA_SOURCE
    return person


def _upsert_meeting(db: Session, provider: str, scraped: ScrapedMeeting, requested_date: date) -> tuple[Meeting, list[str]]:
    track_name = scraped.track_name or "Unknown"
    external_id = scraped.external_id or stable_id(provider, requested_date, track_name)
    meeting_date = scraped.meeting_date or requested_date
    quality, missing = _quality({"track_name": scraped.track_name, "meeting_date": meeting_date})
    meeting = db.query(Meeting).filter(Meeting.provider == provider, Meeting.external_id == external_id).one_or_none()
    if not meeting:
        meeting = Meeting(provider=provider, data_source=WEB_DATA_SOURCE, external_id=external_id, meeting_date=meeting_date, track_name=track_name)
        db.add(meeting)
        db.flush()
    meeting.data_source = WEB_DATA_SOURCE
    meeting.meeting_date = meeting_date
    meeting.track_name = track_name
    meeting.country = scraped.country
    meeting.state = scraped.state
    meeting.track_condition = scraped.track_condition
    meeting.weather = scraped.weather
    meeting.data_quality_status = quality
    meeting.missing_data_fields = missing
    meeting.raw_payload = {"source_label": "web-sourced data", **scraped.raw_payload}
    return meeting, missing


def _upsert_race(db: Session, provider: str, meeting: Meeting, scraped: ScrapedRace) -> tuple[Race, list[str]]:
    name = scraped.name or f"Race {scraped.race_number or ''}".strip() or "Unknown Race"
    external_id = scraped.external_id or stable_id(provider, meeting.external_id, scraped.race_number, name)
    start_time = scraped.start_time or datetime.combine(meeting.meeting_date, time.min, tzinfo=timezone.utc)
    quality, missing = _quality({"name": scraped.name, "start_time": scraped.start_time})
    race = db.query(Race).filter(Race.provider == provider, Race.external_id == external_id).one_or_none()
    if not race:
        race = Race(provider=provider, data_source=WEB_DATA_SOURCE, external_id=external_id, meeting_id=meeting.id, name=name, start_time=start_time)
        db.add(race)
        db.flush()
    race.meeting_id = meeting.id
    race.data_source = WEB_DATA_SOURCE
    race.race_number = scraped.race_number
    race.name = name
    race.start_time = start_time
    race.distance_meters = scraped.distance_meters
    race.race_class = scraped.race_class
    race.status = scraped.status or "scheduled"
    race.track_condition = scraped.track_condition or meeting.track_condition
    race.data_quality_status = quality
    race.missing_data_fields = missing
    race.raw_payload = {"source_label": "web-sourced data", **scraped.raw_payload}
    return race, missing


def _match_runner(race: Race, external_id: str | None, horse_name: str | None) -> Runner | None:
    if external_id:
        for runner in race.runners:
            if runner.external_id == external_id:
                return runner
    wanted = normalize_name(horse_name)
    if not wanted:
        return None
    for runner in race.runners:
        if normalize_name(runner.horse_name) == wanted:
            return runner
    for runner in race.runners:
        existing = normalize_name(runner.horse_name)
        if wanted in existing or existing in wanted:
            return runner
    return None


def _upsert_runner(db: Session, provider: str, race: Race, scraped: ScrapedRunner) -> tuple[Runner, list[str]]:
    horse_name = scraped.horse_name or "Unknown"
    external_id = scraped.external_id or stable_id(provider, race.external_id, horse_name)
    jockey = _get_or_create_person(db, Jockey, provider, scraped.jockey)
    trainer = _get_or_create_person(db, Trainer, provider, scraped.trainer)
    quality, missing = _quality({
        "horse_name": scraped.horse_name,
        "barrier": scraped.barrier,
        "jockey": scraped.jockey,
        "trainer": scraped.trainer,
        "weight_kg": scraped.weight_kg,
    })
    runner = _match_runner(race, external_id, horse_name)
    if not runner:
        runner = Runner(provider=provider, data_source=WEB_DATA_SOURCE, external_id=external_id, race_id=race.id, horse_name=horse_name)
        db.add(runner)
        db.flush()
    runner.data_source = WEB_DATA_SOURCE
    runner.external_id = external_id
    runner.horse_name = horse_name
    runner.barrier = scraped.barrier
    runner.weight_kg = scraped.weight_kg
    runner.jockey_id = jockey.id if jockey else None
    runner.trainer_id = trainer.id if trainer else None
    runner.scratched = scraped.scratched
    runner.past_form = scraped.past_form
    runner.data_quality_status = quality
    runner.missing_data_fields = missing
    runner.raw_payload = {"source_label": "web-sourced data", **scraped.raw_payload}
    return runner, missing


def _latest_odds(db: Session, race_id: int, runner_id: int, bookmaker: str, market_type: str) -> OddsSnapshot | None:
    return (
        db.query(OddsSnapshot)
        .filter(
            OddsSnapshot.race_id == race_id,
            OddsSnapshot.runner_id == runner_id,
            OddsSnapshot.bookmaker == bookmaker,
            OddsSnapshot.market_type == market_type,
        )
        .order_by(OddsSnapshot.fetched_at.desc(), OddsSnapshot.id.desc())
        .first()
    )


def _store_odds(db: Session, provider: str, race: Race, scraped: ScrapedOdds) -> tuple[bool, list[str]]:
    runner = _match_runner(race, scraped.runner_external_id, scraped.horse_name)
    quality, missing = _quality({"runner": runner, "odds_decimal": scraped.odds_decimal, "bookmaker": scraped.bookmaker})
    if quality == "insufficient data":
        return False, missing
    bookmaker = scraped.bookmaker or provider
    market_type = scraped.market_type or "win"
    previous = _latest_odds(db, race.id, runner.id, bookmaker, market_type)
    if previous and Decimal(str(previous.odds_decimal)) == scraped.odds_decimal:
        return False, []
    movement = dict(scraped.market_movement or {})
    if previous:
        movement.update({"previous_odds": float(previous.odds_decimal), "new_odds": float(scraped.odds_decimal)})
    db.add(
        OddsSnapshot(
            race_id=race.id,
            runner_id=runner.id,
            provider=provider,
            data_source=WEB_DATA_SOURCE,
            bookmaker=bookmaker,
            market_type=market_type,
            odds_decimal=scraped.odds_decimal,
            market_movement=movement,
            raw_payload={"source_label": "web-sourced data", **scraped.raw_payload},
        )
    )
    return True, []


def _store_result(db: Session, provider: str, race: Race, scraped: ScrapedResult) -> tuple[bool, list[str]]:
    runner = _match_runner(race, scraped.runner_external_id, scraped.horse_name)
    quality, missing = _quality({"runner": runner, "position": scraped.position})
    if quality == "insufficient data":
        return False, missing
    result = db.query(Result).filter(Result.race_id == race.id, Result.runner_id == runner.id).one_or_none()
    if not result:
        result = Result(race_id=race.id, runner_id=runner.id, provider=provider, data_source=WEB_DATA_SOURCE)
        db.add(result)
    result.provider = provider
    result.data_source = WEB_DATA_SOURCE
    result.position = scraped.position
    result.margin = scraped.margin
    result.starting_price = scraped.starting_price
    result.result_status = scraped.result_status
    result.raw_payload = {"source_label": "web-sourced data", **scraped.raw_payload}
    return True, []


def _store_scraped_meeting(db: Session, provider: str, scraped: ScrapedMeeting, requested_date: date) -> tuple[int, list[str], set[int]]:
    records = 0
    missing_fields: list[str] = []
    rating_race_ids: set[int] = set()
    meeting, missing = _upsert_meeting(db, provider, scraped, requested_date)
    missing_fields.extend(f"meeting.{field}" for field in missing)
    records += 1
    for scraped_race in scraped.races:
        race, missing = _upsert_race(db, provider, meeting, scraped_race)
        missing_fields.extend(f"race.{field}" for field in missing)
        records += 1
        for scraped_runner in scraped_race.runners:
            _, missing = _upsert_runner(db, provider, race, scraped_runner)
            missing_fields.extend(f"runner.{field}" for field in missing)
            records += 1
        db.flush()
        db.expire(race, ["runners"])
        for scraped_odds in scraped_race.odds:
            stored, missing = _store_odds(db, provider, race, scraped_odds)
            missing_fields.extend(f"odds.{field}" for field in missing)
            if stored:
                records += 1
            if not missing:
                rating_race_ids.add(race.id)
        for scraped_result in scraped_race.results:
            stored, missing = _store_result(db, provider, race, scraped_result)
            missing_fields.extend(f"result.{field}" for field in missing)
            if stored:
                records += 1
    return records, missing_fields, rating_race_ids


def sync_scraper(db: Session, scraper: BaseRacingScraper, race_date: date) -> SyncRun:
    run = _start_scrape_run(db, scraper.source_name, race_date)
    records = 0
    missing_fields: list[str] = []
    try:
        scrape_result = scraper.scrape(race_date)
        _attach_scrape_diagnostics(run, scrape_result)
        if scrape_result.status in {"failed", "unavailable"}:
            return _finish_run(db, run, scrape_result.status, 0, scrape_result.missing_data_fields, scrape_result.error_message)
        provider = f"web:{scraper.source_name}"
        for meeting in scrape_result.meetings:
            count, missing, rating_race_ids = _store_scraped_meeting(db, provider, meeting, race_date)
            records += count
            missing_fields.extend(missing)
            db.flush()
            for race_id in rating_race_ids:
                calculate_and_store_model_ratings(db, race_id)
        db.commit()
        status = "completed_with_warnings" if missing_fields or scrape_result.missing_data_fields else "completed"
        missing_fields.extend(scrape_result.missing_data_fields)
        return _finish_run(db, run, status, records, missing_fields)
    except Exception as exc:
        db.rollback()
        logger.exception("Scraping sync failed source=%s", scraper.source_name)
        return _finish_run(db, run, "failed", records, missing_fields, str(exc))


def sync_scraping_sources(db: Session, race_date: date, source: str = "all") -> list[SyncRun]:
    runs: list[SyncRun] = []
    for scraper in configured_scrapers(source):
        runs.append(sync_scraper(db, scraper, race_date))
    return runs
