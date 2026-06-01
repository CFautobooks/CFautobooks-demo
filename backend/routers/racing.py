from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from backend.core.config import settings
from backend.core.database import get_db
from backend.models.racing import Meeting, ModelRating, OddsSnapshot, Race, Result, Runner
from backend.services.racing.calculations import expected_value, fair_odds_from_probability
from backend.services.racing.sync import (
    calculate_and_store_model_ratings,
    sync_all,
    sync_odds,
    sync_racecards,
    sync_results,
    sync_status,
)

router = APIRouter(prefix="/racing", tags=["racing"])


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if settings.ADMIN_API_TOKEN and x_admin_token != settings.ADMIN_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def _runner_payload(runner: Runner, rating: ModelRating | None, odds: OddsSnapshot | None) -> dict[str, Any]:
    return {
        "id": runner.id,
        "external_id": runner.external_id,
        "horse_name": runner.horse_name,
        "barrier": runner.barrier,
        "weight_kg": float(runner.weight_kg) if runner.weight_kg is not None else None,
        "jockey": runner.jockey.name if runner.jockey else None,
        "trainer": runner.trainer.name if runner.trainer else None,
        "scratched": runner.scratched,
        "data_quality_status": runner.data_quality_status,
        "missing_data_fields": runner.missing_data_fields,
        "latest_odds": float(odds.odds_decimal) if odds else None,
        "bookmaker": odds.bookmaker if odds else None,
        "model_rating": None
        if not rating
        else {
            "win_probability": rating.win_probability,
            "fair_odds": float(rating.fair_odds) if rating.fair_odds is not None else None,
            "expected_value": rating.expected_value,
            "confidence_score": rating.confidence_score,
            "confidence_label": rating.confidence_label,
            "data_quality_status": rating.data_quality_status,
            "missing_data_fields": rating.missing_data_fields,
            "calculation_inputs": rating.calculation_inputs,
        },
    }


def _latest_odds_by_runner(db: Session, race_id: int) -> dict[int, OddsSnapshot]:
    latest_ids = (
        db.query(func.max(OddsSnapshot.id).label("id"))
        .filter(OddsSnapshot.race_id == race_id, OddsSnapshot.market_type == "win")
        .group_by(OddsSnapshot.runner_id, OddsSnapshot.bookmaker)
        .subquery()
    )
    rows = db.query(OddsSnapshot).join(latest_ids, OddsSnapshot.id == latest_ids.c.id).all()
    best: dict[int, OddsSnapshot] = {}
    for row in rows:
        current = best.get(row.runner_id)
        if current is None or row.odds_decimal > current.odds_decimal:
            best[row.runner_id] = row
    return best


@router.get("/dashboard/daily")
def daily_race_dashboard(
    race_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    meetings = (
        db.query(Meeting)
        .options(joinedload(Meeting.races).joinedload(Race.runners).joinedload(Runner.jockey))
        .options(joinedload(Meeting.races).joinedload(Race.runners).joinedload(Runner.trainer))
        .filter(Meeting.meeting_date == race_date)
        .order_by(Meeting.track_name)
        .all()
    )
    race_ids = [race.id for meeting in meetings for race in meeting.races]
    ratings = {
        (rating.race_id, rating.runner_id): rating
        for rating in db.query(ModelRating).filter(ModelRating.race_id.in_(race_ids)).all()
    } if race_ids else {}
    payload = []
    for meeting in meetings:
        races = []
        for race in sorted(meeting.races, key=lambda item: item.start_time):
            latest_odds = _latest_odds_by_runner(db, race.id)
            races.append(
                {
                    "id": race.id,
                    "external_id": race.external_id,
                    "race_number": race.race_number,
                    "name": race.name,
                    "start_time": race.start_time,
                    "distance_meters": race.distance_meters,
                    "race_class": race.race_class,
                    "status": race.status,
                    "track_condition": race.track_condition,
                    "data_quality_status": race.data_quality_status,
                    "missing_data_fields": race.missing_data_fields,
                    "runners": [
                        _runner_payload(runner, ratings.get((race.id, runner.id)), latest_odds.get(runner.id))
                        for runner in race.runners
                    ],
                }
            )
        payload.append(
            {
                "id": meeting.id,
                "track_name": meeting.track_name,
                "meeting_date": meeting.meeting_date,
                "country": meeting.country,
                "state": meeting.state,
                "track_condition": meeting.track_condition,
                "weather": meeting.weather,
                "data_quality_status": meeting.data_quality_status,
                "missing_data_fields": meeting.missing_data_fields,
                "races": races,
            }
        )
    return {"date": race_date, "meetings": payload}


@router.get("/dashboard/best-bets")
def best_bets_dashboard(
    race_date: date = Query(default_factory=date.today),
    min_expected_value: float = 0.0,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = (
        db.query(ModelRating)
        .join(Race)
        .join(Runner, Runner.id == ModelRating.runner_id)
        .join(Meeting, Meeting.id == Race.meeting_id)
        .filter(Meeting.meeting_date == race_date)
        .filter(ModelRating.data_quality_status == "sufficient")
        .filter(ModelRating.expected_value > min_expected_value)
        .order_by(desc(ModelRating.expected_value), desc(ModelRating.confidence_score))
        .limit(25)
        .all()
    )
    return {
        "date": race_date,
        "min_expected_value": min_expected_value,
        "bets": [
            {
                "race_id": rating.race_id,
                "runner_id": rating.runner_id,
                "track": rating.race.meeting.track_name,
                "race": rating.race.name,
                "horse_name": rating.runner.horse_name,
                "win_probability": rating.win_probability,
                "fair_odds": float(rating.fair_odds) if rating.fair_odds is not None else None,
                "bookmaker_odds": float(rating.bookmaker_odds) if rating.bookmaker_odds is not None else None,
                "expected_value": rating.expected_value,
                "confidence_score": rating.confidence_score,
                "confidence_label": rating.confidence_label,
                "calculation_inputs": rating.calculation_inputs,
            }
            for rating in rows
        ],
    }


@router.get("/calculators/fair-odds")
def fair_odds_calculator(probability: float = Query(gt=0, lt=1)) -> dict[str, float | None]:
    return {"probability": probability, "fair_odds": fair_odds_from_probability(probability)}


@router.get("/calculators/expected-value")
def expected_value_calculator(
    probability: float = Query(gt=0, lt=1),
    decimal_odds: float = Query(gt=1),
) -> dict[str, float | None]:
    return {
        "probability": probability,
        "decimal_odds": decimal_odds,
        "expected_value": expected_value(probability, decimal_odds),
    }


@router.get("/results/tracker")
def results_tracker(
    race_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    results = (
        db.query(Result)
        .join(Race)
        .join(Meeting)
        .filter(Meeting.meeting_date == race_date)
        .order_by(Race.start_time, Result.position)
        .all()
    )
    return {
        "date": race_date,
        "results": [
            {
                "track": result.race.meeting.track_name,
                "race": result.race.name,
                "horse_name": result.runner.horse_name,
                "position": result.position,
                "margin": float(result.margin) if result.margin is not None else None,
                "starting_price": float(result.starting_price) if result.starting_price is not None else None,
                "result_status": result.result_status,
            }
            for result in results
        ],
    }




def _sync_run_payload(run: Any) -> dict[str, Any]:
    return {
        "id": run.id,
        "provider": run.provider,
        "sync_type": run.sync_type,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "records_processed": run.records_processed,
        "missing_data_fields": run.missing_data_fields,
        "error_message": run.error_message,
    }


@router.get("/admin/sync-status", dependencies=[Depends(require_admin_token)])
def admin_sync_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    return sync_status(db)


@router.post("/admin/sync", dependencies=[Depends(require_admin_token)])
def admin_trigger_sync(
    sync_type: str = Query(default="all", pattern="^(all|racecards|odds|results|ratings)$"),
    race_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if sync_type == "all":
        runs = sync_all(db, race_date)
        return {"sync_type": sync_type, "runs": [_sync_run_payload(run) for run in runs]}
    if sync_type == "racecards":
        return {"sync_type": sync_type, "run": _sync_run_payload(sync_racecards(db, race_date))}
    if sync_type == "odds":
        return {"sync_type": sync_type, "run": _sync_run_payload(sync_odds(db))}
    if sync_type == "results":
        return {"sync_type": sync_type, "run": _sync_run_payload(sync_results(db, race_date))}
    races = db.query(Race).join(Meeting).filter(Meeting.meeting_date == race_date).all()
    ratings = []
    for race in races:
        ratings.extend(calculate_and_store_model_ratings(db, race.id))
    db.commit()
    return {"sync_type": sync_type, "ratings_created": len(ratings)}
