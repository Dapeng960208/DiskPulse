# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Integer, and_, case, cast, exists, func, or_, select, update
from sqlalchemy.orm import aliased

from models import (
    CapacityForecast,
    CapacityPredictionPlan,
    CapacityPredictionSettings,
    CapacityPredictionCandidate,
    CapacityPredictionEvaluation,
    CapacityPredictionCandidateForecast,
    Group,
    StorageUsage,
)


def _safe_integer_asset_id(column):
    """Guard PostgreSQL's strict integer cast against malformed historical IDs."""
    non_digits = column
    for digit in "0123456789":
        non_digits = func.replace(non_digits, digit, "")
    length = func.length(column)
    return case(
        (
            and_(
                length.between(1, 10),
                non_digits == "",
                or_(length < 10, column <= "2147483647"),
            ),
            cast(column, Integer),
        ),
        else_=None,
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


def list_latest_forecasts(
    db,
    *,
    visible_project_ids: set[int] | None,
    page: int,
    size: int,
) -> tuple[list[CapacityForecast], int]:
    newer = aliased(CapacityForecast)
    newer_exists = exists(
        select(newer.id).where(
            newer.asset_type == CapacityForecast.asset_type,
            newer.asset_id == CapacityForecast.asset_id,
            or_(
                newer.training_end > CapacityForecast.training_end,
                and_(
                    newer.training_end == CapacityForecast.training_end,
                    newer.created_at > CapacityForecast.created_at,
                ),
                and_(
                    newer.training_end == CapacityForecast.training_end,
                    newer.created_at == CapacityForecast.created_at,
                    newer.id > CapacityForecast.id,
                ),
            ),
        )
    )
    current_asset_id = _safe_integer_asset_id(CapacityForecast.asset_id)
    group_conditions = [Group.id == current_asset_id]
    usage_conditions = [StorageUsage.id == current_asset_id]
    if visible_project_ids is not None:
        group_conditions.append(Group.project_id.in_(visible_project_ids))
        usage_conditions.append(Group.project_id.in_(visible_project_ids))
    current_resource_exists = or_(
        and_(
            CapacityForecast.asset_type == "group",
            exists(select(Group.id).where(*group_conditions)),
        ),
        and_(
            CapacityForecast.asset_type == "storage_usage",
            exists(
                select(StorageUsage.id)
                .join(Group, Group.id == StorageUsage.group_id)
                .where(*usage_conditions)
            ),
        ),
    )
    statement = select(CapacityForecast).where(
        CapacityForecast.asset_type.in_(("group", "storage_usage")),
        current_resource_exists,
        ~newer_exists,
    )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(
        statement.order_by(CapacityForecast.created_at.desc(), CapacityForecast.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()
    return rows, int(total)


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


def list_candidate_forecasts_for_baselines(
    db,
    *,
    candidate_id: int,
    baseline_keys: list[tuple[str, str, datetime]],
) -> list[CapacityPredictionCandidateForecast]:
    if not baseline_keys:
        return []
    matches = [
        and_(
            CapacityPredictionCandidateForecast.asset_type == asset_type,
            CapacityPredictionCandidateForecast.asset_id == asset_id,
            CapacityPredictionCandidateForecast.forecast_start == forecast_start,
        )
        for asset_type, asset_id, forecast_start in baseline_keys
    ]
    return db.execute(
        select(CapacityPredictionCandidateForecast).where(
            CapacityPredictionCandidateForecast.candidate_id == candidate_id,
            or_(*matches),
        )
    ).scalars().all()


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
