from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.models.racing import (
    Jockey,
    Meeting,
    ModelRating,
    OddsSnapshot,
    Race,
    Result,
    Runner,
    SyncRun,
    Trainer,
)
from backend.services.racing.calculations import CALCULATION_VERSION, RunnerRatingInput, calculate_race_ratings
from backend.services.racing.providers import (
    OddsProvider,
    ProviderConfigurationError,
    RacingFormProvider,
    get_odds_provider,
    get_racing_form_provider,
)

logger = logging.getLogger(__name__)


def _first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _nested_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return _first(value, "name", "full_name", "display_name")
    if isinstance(value, str):
        return value
    return None


def _nested_external_id(value: Any, fallback: str | None = None) -> str | None:
    if isinstance(value, dict):
        return str(_first(value, "id", "external_id", "provider_id", "key") or fallback or "")
    return fallback


def _list_from(payload: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _parse_datetime(value: Any, fallback_date: date | None = None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            if fallback_date:
                try:
                    parsed_time = time.fromisoformat(value[:8])
                    return datetime.combine(fallback_date, parsed_time, tzinfo=timezone.utc)
                except ValueError:
                    return None
    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _quality(required: dict[str, Any]) -> tuple[str, list[str]]:
    missing = [field for field, value in required.items() if value in (None, "", [])]
    return ("insufficient data" if missing else "sufficient", missing)


def _start_sync_run(db: Session, provider: str, sync_type: str, metadata: dict[str, Any] | None = None) -> SyncRun:
    sync_run = SyncRun(provider=provider, sync_type=sync_type, status="running", metadata_json=metadata or {})
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)
    return sync_run


def _finish_sync_run(
    db: Session,
    sync_run: SyncRun,
    status: str,
    records_processed: int,
    missing_fields: list[str] | None = None,
    error_message: str | None = None,
) -> SyncRun:
    sync_run.status = status
    sync_run.completed_at = datetime.now(timezone.utc)
    sync_run.records_processed = records_processed
    sync_run.missing_data_fields = sorted(set(missing_fields or []))
    sync_run.error_message = error_message
    db.commit()
    db.refresh(sync_run)
    if missing_fields:
        logger.warning("Racing sync completed with missing fields: %s", sorted(set(missing_fields)))
    return sync_run


def _get_or_create_person(
    db: Session,
    model: type[Jockey] | type[Trainer],
    provider: str,
    value: Any,
    fallback_name: str | None,
) -> Jockey | Trainer | None:
    name = _nested_name(value) or fallback_name
    external_id = _nested_external_id(value, name)
    if not name or not external_id:
        return None
    person = (
        db.query(model)
        .filter(model.provider == provider, model.external_id == str(external_id))
        .one_or_none()
    )
    if not person:
        person = model(provider=provider, external_id=str(external_id), name=name, raw_payload=value if isinstance(value, dict) else {})
        db.add(person)
        db.flush()
    else:
        person.name = name
        person.raw_payload = value if isinstance(value, dict) else person.raw_payload
    return person


def _upsert_meeting(db: Session, provider: str, payload: dict[str, Any], requested_date: date) -> tuple[Meeting, list[str]]:
    external_id = str(_first(payload, "id", "external_id", "meeting_id", "key") or "")
    meeting_date = _parse_date(_first(payload, "date", "meeting_date")) or requested_date
    track_name = _first(payload, "track_name", "track", "venue", "name")
    quality_status, missing = _quality({"external_id": external_id, "track_name": track_name, "meeting_date": meeting_date})
    if not external_id:
        external_id = f"{meeting_date.isoformat()}:{track_name or 'unknown-track'}"

    meeting = (
        db.query(Meeting)
        .filter(Meeting.provider == provider, Meeting.external_id == external_id)
        .one_or_none()
    )
    if not meeting:
        meeting = Meeting(provider=provider, external_id=external_id, meeting_date=meeting_date, track_name=track_name or "Unknown")
        db.add(meeting)
        db.flush()
    meeting.meeting_date = meeting_date
    meeting.track_name = track_name or meeting.track_name
    meeting.country = _first(payload, "country")
    meeting.state = _first(payload, "state", "region")
    meeting.track_condition = _first(payload, "track_condition", "going", "surface_condition")
    meeting.weather = _first(payload, "weather")
    meeting.data_quality_status = quality_status
    meeting.missing_data_fields = missing
    meeting.raw_payload = payload
    return meeting, missing


def _upsert_race(
    db: Session,
    provider: str,
    meeting: Meeting,
    payload: dict[str, Any],
) -> tuple[Race, list[str]]:
    race_number = _to_int(_first(payload, "race_number", "number", "race_no"))
    external_id = str(_first(payload, "id", "external_id", "race_id", "key") or "")
    if not external_id:
        external_id = f"{meeting.external_id}:race:{race_number or _first(payload, 'name', 'race_name') or 'unknown'}"
    name = _first(payload, "name", "race_name", "title") or f"Race {race_number or ''}".strip()
    start_time = _parse_datetime(_first(payload, "start_time", "start", "jump_time"), meeting.meeting_date)
    quality_status, missing = _quality({"external_id": external_id, "name": name, "start_time": start_time})

    race = db.query(Race).filter(Race.provider == provider, Race.external_id == external_id).one_or_none()
    if not race:
        race = Race(
            provider=provider,
            external_id=external_id,
            meeting_id=meeting.id,
            name=name,
            start_time=start_time or datetime.combine(meeting.meeting_date, time.min, tzinfo=timezone.utc),
        )
        db.add(race)
        db.flush()
    race.meeting_id = meeting.id
    race.race_number = race_number
    race.name = name
    race.start_time = start_time or race.start_time
    race.distance_meters = _to_int(_first(payload, "distance_meters", "distance", "distance_metres"))
    race.race_class = _first(payload, "class", "race_class", "grade")
    race.status = _first(payload, "status") or race.status or "scheduled"
    race.track_condition = _first(payload, "track_condition", "going") or meeting.track_condition
    race.data_quality_status = quality_status
    race.missing_data_fields = missing
    race.raw_payload = payload
    return race, missing


def _upsert_runner(db: Session, provider: str, race: Race, payload: dict[str, Any]) -> tuple[Runner, list[str]]:
    external_id = str(_first(payload, "id", "external_id", "runner_id", "horse_id", "key") or "")
    horse_name = _first(payload, "horse_name", "name", "runner_name")
    if not external_id:
        external_id = f"{race.external_id}:runner:{horse_name or 'unknown'}"
    jockey = _get_or_create_person(db, Jockey, provider, payload.get("jockey"), _first(payload, "jockey_name"))
    trainer = _get_or_create_person(db, Trainer, provider, payload.get("trainer"), _first(payload, "trainer_name"))
    quality_status, missing = _quality(
        {
            "external_id": external_id,
            "horse_name": horse_name,
            "barrier": _first(payload, "barrier", "draw"),
            "weight_kg": _first(payload, "weight_kg", "weight"),
            "past_form": _first(payload, "past_form", "form"),
        }
    )

    runner = (
        db.query(Runner)
        .filter(Runner.race_id == race.id, Runner.provider == provider, Runner.external_id == external_id)
        .one_or_none()
    )
    if not runner:
        runner = Runner(provider=provider, external_id=external_id, race_id=race.id, horse_name=horse_name or "Unknown")
        db.add(runner)
        db.flush()
    runner.horse_name = horse_name or runner.horse_name
    runner.barrier = _to_int(_first(payload, "barrier", "draw"))
    runner.weight_kg = _to_decimal(_first(payload, "weight_kg", "weight"))
    runner.jockey_id = jockey.id if jockey else None
    runner.trainer_id = trainer.id if trainer else None
    runner.past_form = _first(payload, "past_form", "form") or []
    runner.scratched = bool(_first(payload, "scratched", "is_scratched") or False)
    runner.data_quality_status = quality_status
    runner.missing_data_fields = missing
    runner.raw_payload = payload
    return runner, missing


def sync_racecards(db: Session, race_date: date, provider: RacingFormProvider | None = None) -> SyncRun:
    records = 0
    missing_fields: list[str] = []
    sync_run: SyncRun | None = None
    try:
        provider = provider or get_racing_form_provider()
        sync_run = _start_sync_run(db, provider.name, "racecards", {"date": race_date.isoformat()})
        meetings_payload = provider.fetch_meetings(race_date)
        for meeting_payload in meetings_payload:
            meeting, missing = _upsert_meeting(db, provider.name, meeting_payload, race_date)
            missing_fields.extend([f"meeting.{field}" for field in missing])
            racecard_payload = provider.fetch_racecard(meeting.external_id)
            races_payload = _list_from(racecard_payload, "races", "racecards") or _list_from(meeting_payload, "races")
            for race_payload in races_payload:
                race, missing = _upsert_race(db, provider.name, meeting, race_payload)
                missing_fields.extend([f"race.{field}" for field in missing])
                for runner_payload in _list_from(race_payload, "runners", "horses", "entries"):
                    _, runner_missing = _upsert_runner(db, provider.name, race, runner_payload)
                    missing_fields.extend([f"runner.{field}" for field in runner_missing])
                    records += 1
        db.commit()
        status = "completed_with_warnings" if missing_fields else "completed"
        return _finish_sync_run(db, sync_run, status, records, missing_fields)
    except Exception as exc:
        db.rollback()
        message = str(exc)
        if sync_run:
            return _finish_sync_run(db, sync_run, "failed", records, missing_fields, message)
        provider_name = getattr(provider, "name", "racing_form")
        sync_run = _start_sync_run(db, provider_name, "racecards", {"date": race_date.isoformat()})
        return _finish_sync_run(db, sync_run, "failed", records, missing_fields, message)


def sync_odds(db: Session, provider: OddsProvider | None = None) -> SyncRun:
    records = 0
    missing_fields: list[str] = []
    sync_run: SyncRun | None = None
    try:
        provider = provider or get_odds_provider()
        sync_run = _start_sync_run(db, provider.name, "odds")
        races = db.query(Race).filter(Race.status.in_(["scheduled", "open", "betting"])).all()
        for race in races:
            odds_payloads = provider.fetch_odds(race.external_id)
            runners_by_external = {runner.external_id: runner for runner in race.runners}
            runners_by_name = {runner.horse_name.lower(): runner for runner in race.runners}
            for payload in odds_payloads:
                runner_key = str(_first(payload, "runner_id", "runner_external_id", "horse_id") or "")
                runner_name = str(_first(payload, "horse_name", "runner_name", "name") or "").lower()
                runner = runners_by_external.get(runner_key) or runners_by_name.get(runner_name)
                odds_decimal = _to_decimal(_first(payload, "odds_decimal", "decimal_odds", "price"))
                bookmaker = _first(payload, "bookmaker", "bookmaker_name", "source")
                quality_status, missing = _quality({"runner": runner, "odds_decimal": odds_decimal, "bookmaker": bookmaker})
                if missing:
                    missing_fields.extend([f"odds.{field}" for field in missing])
                if quality_status == "insufficient data":
                    continue
                db.add(
                    OddsSnapshot(
                        race_id=race.id,
                        runner_id=runner.id,
                        provider=provider.name,
                        bookmaker=bookmaker,
                        market_type=_first(payload, "market_type", "market") or "win",
                        odds_decimal=odds_decimal,
                        market_movement=_first(payload, "market_movement", "movement") or {},
                        raw_payload=payload,
                    )
                )
                records += 1
            calculate_and_store_model_ratings(db, race.id)
        db.commit()
        status = "completed_with_warnings" if missing_fields else "completed"
        return _finish_sync_run(db, sync_run, status, records, missing_fields)
    except Exception as exc:
        db.rollback()
        message = str(exc)
        if sync_run:
            return _finish_sync_run(db, sync_run, "failed", records, missing_fields, message)
        provider_name = getattr(provider, "name", "odds")
        sync_run = _start_sync_run(db, provider_name, "odds")
        return _finish_sync_run(db, sync_run, "failed", records, missing_fields, message)


def sync_results(db: Session, race_date: date, provider: RacingFormProvider | None = None) -> SyncRun:
    records = 0
    missing_fields: list[str] = []
    sync_run: SyncRun | None = None
    try:
        provider = provider or get_racing_form_provider()
        sync_run = _start_sync_run(db, provider.name, "results", {"date": race_date.isoformat()})
        results_payload = provider.fetch_results(race_date)
        races_by_external = {race.external_id: race for race in db.query(Race).all()}
        for payload in results_payload:
            race = races_by_external.get(str(_first(payload, "race_id", "race_external_id") or ""))
            runner_external_id = str(_first(payload, "runner_id", "runner_external_id", "horse_id") or "")
            runner_name = str(_first(payload, "horse_name", "runner_name", "name") or "").lower()
            runner = None
            if race:
                runner = next((item for item in race.runners if item.external_id == runner_external_id), None)
                runner = runner or next((item for item in race.runners if item.horse_name.lower() == runner_name), None)
            position = _to_int(_first(payload, "position", "finish_position"))
            quality_status, missing = _quality({"race": race, "runner": runner, "position": position})
            if missing:
                missing_fields.extend([f"result.{field}" for field in missing])
            if quality_status == "insufficient data":
                continue
            result = db.query(Result).filter(Result.race_id == race.id, Result.runner_id == runner.id).one_or_none()
            if not result:
                result = Result(race_id=race.id, runner_id=runner.id, provider=provider.name)
                db.add(result)
            result.position = position
            result.margin = _to_decimal(_first(payload, "margin", "beaten_margin"))
            result.starting_price = _to_decimal(_first(payload, "starting_price", "sp"))
            result.result_status = _first(payload, "result_status", "status") or "official"
            result.raw_payload = payload
            records += 1
        db.commit()
        status = "completed_with_warnings" if missing_fields else "completed"
        return _finish_sync_run(db, sync_run, status, records, missing_fields)
    except Exception as exc:
        db.rollback()
        message = str(exc)
        if sync_run:
            return _finish_sync_run(db, sync_run, "failed", records, missing_fields, message)
        provider_name = getattr(provider, "name", "racing_form")
        sync_run = _start_sync_run(db, provider_name, "results", {"date": race_date.isoformat()})
        return _finish_sync_run(db, sync_run, "failed", records, missing_fields, message)


def _latest_runner_odds(db: Session, race_id: int) -> dict[int, float]:
    latest_ids = (
        db.query(func.max(OddsSnapshot.id).label("id"))
        .filter(OddsSnapshot.race_id == race_id, OddsSnapshot.market_type == "win")
        .group_by(OddsSnapshot.runner_id, OddsSnapshot.bookmaker)
        .subquery()
    )
    odds_rows = db.query(OddsSnapshot).join(latest_ids, OddsSnapshot.id == latest_ids.c.id).all()
    best_odds: dict[int, float] = {}
    for row in odds_rows:
        current = best_odds.get(row.runner_id)
        value = float(row.odds_decimal)
        if current is None or value > current:
            best_odds[row.runner_id] = value
    return best_odds


def calculate_and_store_model_ratings(db: Session, race_id: int) -> list[ModelRating]:
    race = db.query(Race).filter(Race.id == race_id).one()
    latest_odds = _latest_runner_odds(db, race_id)
    inputs = [
        RunnerRatingInput(runner=runner, latest_odds=latest_odds.get(runner.id))
        for runner in race.runners
        if not runner.scratched
    ]
    outputs = calculate_race_ratings(inputs)
    stored: list[ModelRating] = []
    for output in outputs:
        rating = (
            db.query(ModelRating)
            .filter(
                ModelRating.race_id == race_id,
                ModelRating.runner_id == output.runner_id,
                ModelRating.calculation_version == CALCULATION_VERSION,
            )
            .one_or_none()
        )
        if not rating:
            rating = ModelRating(race_id=race_id, runner_id=output.runner_id, calculation_version=CALCULATION_VERSION)
            db.add(rating)
        rating.win_probability = output.win_probability
        rating.fair_odds = _to_decimal(output.fair_odds)
        rating.bookmaker_odds = _to_decimal(output.bookmaker_odds)
        rating.expected_value = output.expected_value
        rating.confidence_score = output.confidence_score
        rating.confidence_label = output.confidence_label
        rating.rating_score = output.rating_score
        rating.suggested_staking_unit = output.suggested_staking_unit
        rating.data_quality_status = output.data_quality_status
        rating.missing_data_fields = output.missing_data_fields
        rating.calculation_inputs = output.calculation_inputs
        stored.append(rating)
    db.flush()
    return stored


def sync_all(db: Session, race_date: date) -> list[SyncRun]:
    runs = [sync_racecards(db, race_date)]
    runs.append(sync_odds(db))
    runs.append(sync_results(db, race_date))
    return runs


def sync_status(db: Session, limit: int = 20) -> dict[str, Any]:
    recent_runs = db.query(SyncRun).order_by(desc(SyncRun.started_at)).limit(limit).all()
    latest_by_type: dict[str, SyncRun] = {}
    for run in recent_runs:
        latest_by_type.setdefault(f"{run.provider}:{run.sync_type}", run)
    missing_counts: dict[str, int] = defaultdict(int)
    for run in recent_runs:
        for field in run.missing_data_fields or []:
            missing_counts[field] += 1
    return {
        "latest": [
            {
                "provider": run.provider,
                "sync_type": run.sync_type,
                "status": run.status,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "records_processed": run.records_processed,
                "error_message": run.error_message,
                "missing_data_fields": run.missing_data_fields,
            }
            for run in latest_by_type.values()
        ],
        "recent_runs": [
            {
                "id": run.id,
                "provider": run.provider,
                "sync_type": run.sync_type,
                "status": run.status,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "records_processed": run.records_processed,
                "error_message": run.error_message,
                "missing_data_fields": run.missing_data_fields,
                "metadata": run.metadata_json,
            }
            for run in recent_runs
        ],
        "missing_field_counts": dict(missing_counts),
    }
