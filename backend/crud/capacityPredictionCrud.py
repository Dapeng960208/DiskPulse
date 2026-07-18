# -*- coding: utf-8 -*-
from sqlalchemy import func, select, update

from models import (
    CapacityForecast,
    CapacityPredictionPlan,
    CapacityPredictionSettings,
    CapacityPredictionCandidate,
    CapacityPredictionEvaluation,
    CapacityPredictionCandidateForecast,
)


def get_settings(db):
    return db.get(CapacityPredictionSettings, 1)


def get_or_create_settings(db):
    settings = get_settings(db)
    if settings is None:
        settings = CapacityPredictionSettings(id=1, user_visible=False)
        db.add(settings)
        db.flush()
    return settings


def latest_forecast(db, *, asset_type: str, asset_id: str):
    return db.execute(
        select(CapacityForecast)
        .where(CapacityForecast.asset_type == asset_type, CapacityForecast.asset_id == asset_id)
        .order_by(
            CapacityForecast.training_end.desc(),
            CapacityForecast.created_at.desc(),
            CapacityForecast.id.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def add_plan(db, plan: CapacityPredictionPlan) -> CapacityPredictionPlan:
    db.add(plan)
    db.flush()
    return plan


def list_plans(db, *, asset_type: str, asset_id: str) -> list[CapacityPredictionPlan]:
    return db.execute(
        select(CapacityPredictionPlan)
        .where(CapacityPredictionPlan.asset_type == asset_type, CapacityPredictionPlan.asset_id == asset_id)
        .order_by(CapacityPredictionPlan.effective_at.asc(), CapacityPredictionPlan.id.asc())
    ).scalars().all()


def get_candidate(db, candidate_id: int) -> CapacityPredictionCandidate | None:
    return db.get(CapacityPredictionCandidate, candidate_id)


def get_candidate_by_version(db, version: str) -> CapacityPredictionCandidate | None:
    return db.execute(
        select(CapacityPredictionCandidate).where(CapacityPredictionCandidate.version == version)
    ).scalar_one_or_none()


def add_candidate(db, candidate: CapacityPredictionCandidate) -> CapacityPredictionCandidate:
    db.add(candidate)
    db.flush()
    return candidate


def list_candidates(db) -> list[CapacityPredictionCandidate]:
    return db.execute(
        select(CapacityPredictionCandidate).order_by(
            CapacityPredictionCandidate.enabled.desc(),
            CapacityPredictionCandidate.id.desc(),
        )
    ).scalars().all()


def active_candidate(db) -> CapacityPredictionCandidate | None:
    return db.execute(
        select(CapacityPredictionCandidate)
        .where(CapacityPredictionCandidate.enabled.is_(True))
        .order_by(CapacityPredictionCandidate.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def list_candidate_evaluations(db, *, candidate_id: int) -> list[CapacityPredictionEvaluation]:
    return db.execute(
        select(CapacityPredictionEvaluation)
        .where(CapacityPredictionEvaluation.candidate_id == candidate_id)
        .order_by(CapacityPredictionEvaluation.window_end.asc(), CapacityPredictionEvaluation.id.asc())
    ).scalars().all()


def has_candidate_evaluation(db, *, candidate_id: int, window_start, window_end) -> bool:
    return db.execute(
        select(CapacityPredictionEvaluation.id).where(
            CapacityPredictionEvaluation.candidate_id == candidate_id,
            CapacityPredictionEvaluation.window_start == window_start,
            CapacityPredictionEvaluation.window_end == window_end,
        ).limit(1)
    ).scalar_one_or_none() is not None


def add_candidate_evaluation(db, evaluation: CapacityPredictionEvaluation) -> CapacityPredictionEvaluation:
    db.add(evaluation)
    db.flush()
    return evaluation


def get_candidate_forecast(
    db,
    *,
    candidate_id: int,
    asset_type: str,
    asset_id: str,
    forecast_start,
) -> CapacityPredictionCandidateForecast | None:
    return db.execute(
        select(CapacityPredictionCandidateForecast).where(
            CapacityPredictionCandidateForecast.candidate_id == candidate_id,
            CapacityPredictionCandidateForecast.asset_type == asset_type,
            CapacityPredictionCandidateForecast.asset_id == asset_id,
            CapacityPredictionCandidateForecast.forecast_start == forecast_start,
        )
    ).scalar_one_or_none()


def latest_active_candidate_forecast(
    db,
    *,
    asset_type: str,
    asset_id: str,
    forecast_start,
) -> CapacityPredictionCandidateForecast | None:
    return db.execute(
        select(CapacityPredictionCandidateForecast)
        .join(
            CapacityPredictionCandidate,
            CapacityPredictionCandidate.id == CapacityPredictionCandidateForecast.candidate_id,
        )
        .where(
            CapacityPredictionCandidate.enabled.is_(True),
            CapacityPredictionCandidateForecast.asset_type == asset_type,
            CapacityPredictionCandidateForecast.asset_id == asset_id,
            CapacityPredictionCandidateForecast.forecast_start == forecast_start,
        )
        .order_by(
            CapacityPredictionCandidateForecast.forecast_start.desc(),
            CapacityPredictionCandidateForecast.id.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def add_candidate_forecast(
    db,
    forecast: CapacityPredictionCandidateForecast,
) -> CapacityPredictionCandidateForecast:
    db.add(forecast)
    db.flush()
    return forecast


def candidate_forecast_summary(db, *, candidate_id: int) -> dict:
    rows = db.execute(
        select(
            CapacityPredictionCandidateForecast.source,
            CapacityPredictionCandidateForecast.fallback_reason,
            func.count(CapacityPredictionCandidateForecast.id),
        )
        .where(CapacityPredictionCandidateForecast.candidate_id == candidate_id)
        .group_by(
            CapacityPredictionCandidateForecast.source,
            CapacityPredictionCandidateForecast.fallback_reason,
        )
    ).all()
    forecast_count = sum(int(count) for _source, _reason, count in rows)
    fallback_reasons = {
        str(reason or "unknown"): int(count)
        for source, reason, count in rows
        if source == "baseline_fallback"
    }
    return {
        "forecast_count": forecast_count,
        "fallback_count": sum(fallback_reasons.values()),
        "fallback_reasons": fallback_reasons,
    }


def disable_candidates(db) -> None:
    db.execute(update(CapacityPredictionCandidate).values(enabled=False))
