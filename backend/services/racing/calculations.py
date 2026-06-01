from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from backend.models.racing import Runner

CALCULATION_VERSION = "v1"


@dataclass
class RunnerRatingInput:
    runner: Runner
    latest_odds: float | None


@dataclass
class RunnerRatingOutput:
    runner_id: int
    win_probability: float | None
    fair_odds: float | None
    bookmaker_odds: float | None
    expected_value: float | None
    confidence_score: float
    confidence_label: str
    rating_score: float | None
    data_quality_status: str
    missing_data_fields: list[str]
    calculation_inputs: dict[str, Any]


def fair_odds_from_probability(probability: float | None) -> float | None:
    if probability is None or probability <= 0:
        return None
    return round(1 / probability, 3)


def expected_value(probability: float | None, decimal_odds: float | None) -> float | None:
    if probability is None or decimal_odds is None:
        return None
    return round((probability * decimal_odds) - 1, 4)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _past_form_positions(past_form: Any) -> list[int]:
    if isinstance(past_form, list):
        values = past_form
    elif isinstance(past_form, str):
        values = [char for char in past_form if char.isdigit()]
    else:
        values = []

    positions: list[int] = []
    for item in values[:6]:
        if isinstance(item, dict):
            item = item.get("position") or item.get("finish_position")
        try:
            position = int(item)
        except (TypeError, ValueError):
            continue
        if position > 0:
            positions.append(position)
    return positions


def _past_form_score(past_form: Any) -> tuple[float | None, list[int]]:
    positions = _past_form_positions(past_form)
    if not positions:
        return None, []
    average_finish = sum(positions) / len(positions)
    score = max(0.05, min(1.0, 1 - ((average_finish - 1) / 12)))
    return round(score, 4), positions


def _barrier_score(barrier: int | None) -> float | None:
    if barrier is None:
        return None
    return round(max(0.2, 1 - ((barrier - 1) * 0.035)), 4)


def _weight_score(weight_kg: float | None) -> float | None:
    if weight_kg is None:
        return None
    return round(max(0.2, min(1.0, 1 - ((weight_kg - 54) * 0.035))), 4)


def _odds_score(decimal_odds: float | None) -> float | None:
    if decimal_odds is None or decimal_odds <= 1:
        return None
    return round(min(1.0, 1 / decimal_odds), 4)


def _confidence(completeness: float, probability: float | None, field_count: int) -> tuple[float, str]:
    if probability is None or field_count < 3:
        return 0.0, "insufficient data"
    score = round(min(0.95, max(0.05, completeness)), 4)
    if score >= 0.8:
        return score, "high"
    if score >= 0.6:
        return score, "medium"
    return score, "low"


def calculate_race_ratings(runners: list[RunnerRatingInput]) -> list[RunnerRatingOutput]:
    raw_scores: dict[int, float] = {}
    details: dict[int, dict[str, Any]] = {}

    for item in runners:
        runner = item.runner
        past_form_score, positions = _past_form_score(runner.past_form)
        barrier = runner.barrier
        weight_kg = _to_float(runner.weight_kg)
        components = {
            "past_form": past_form_score,
            "market": _odds_score(item.latest_odds),
            "barrier": _barrier_score(barrier),
            "weight": _weight_score(weight_kg),
        }
        missing_fields = [name for name, value in components.items() if value is None]
        available = {name: value for name, value in components.items() if value is not None}
        if len(available) >= 3:
            score = (
                (available.get("past_form", 0) * 0.45)
                + (available.get("market", 0) * 0.30)
                + (available.get("barrier", 0) * 0.15)
                + (available.get("weight", 0) * 0.10)
            )
            raw_scores[runner.id] = max(score, 0.0001)
        details[runner.id] = {
            "components": components,
            "missing_fields": missing_fields,
            "past_form_positions": positions,
            "latest_odds": item.latest_odds,
            "barrier": barrier,
            "weight_kg": weight_kg,
            "scratched": runner.scratched,
        }

    score_total = sum(raw_scores.values())
    outputs: list[RunnerRatingOutput] = []
    for item in runners:
        runner = item.runner
        detail = details[runner.id]
        rating_score = raw_scores.get(runner.id)
        probability = round(rating_score / score_total, 4) if rating_score and score_total else None
        field_count = 4 - len(detail["missing_fields"])
        completeness = field_count / 4
        confidence_score, confidence_label = _confidence(completeness, probability, field_count)
        quality_status = "sufficient" if probability is not None else "insufficient data"
        fair_odds = fair_odds_from_probability(probability)

        outputs.append(
            RunnerRatingOutput(
                runner_id=runner.id,
                win_probability=probability,
                fair_odds=fair_odds,
                bookmaker_odds=item.latest_odds,
                expected_value=expected_value(probability, item.latest_odds),
                confidence_score=confidence_score,
                confidence_label=confidence_label,
                rating_score=round(rating_score, 4) if rating_score else None,
                data_quality_status=quality_status,
                missing_data_fields=detail["missing_fields"],
                calculation_inputs={
                    "calculation_version": CALCULATION_VERSION,
                    "formula": {
                        "past_form": 0.45,
                        "market": 0.30,
                        "barrier": 0.15,
                        "weight": 0.10,
                    },
                    **detail,
                },
            )
        )
    return outputs
