# -*- coding: utf-8 -*-
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal
from types import SimpleNamespace
from utils.datetime_utils import utc_now
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from crud import capacityPredictionCrud, forecastIncidentCrud
from models import (
    AIConfig,
    CapacityPredictionCandidate,
    CapacityPredictionCandidateForecast,
    CapacityPredictionEvaluation,
    CapacityPredictionPlan,
    Project,
    StorageCluster,
)
from services import audit_service, forecastIncidentService, project_access_service
from services.ai_client import AIClientError, chat_completion
from utils.auth_service import is_super_admin


PredictionAssetType = Literal["storage_cluster", "project", "group", "storage_usage"]

RISK_LABELS = {
    "insufficient": "数据不足",
    "critical": "紧急",
    "high": "高风险",
    "watch": "关注",
    "none": "30 日内无耗尽风险",
}


@dataclass(frozen=True)
class CandidateCurveResult:
    curve: list[dict[str, Any]]
    source: Literal["ai_candidate", "baseline_fallback"]
    fallback_reason: str | None = None


def _daily_capacity_points(points: list[tuple[datetime, float]]) -> list[dict[str, float | str]]:
    daily: dict[str, float] = {}
    for observed_at, used in points:
        if observed_at.tzinfo is None:
            continue
        key = observed_at.astimezone(timezone.utc).date().isoformat()
        daily[key] = max(daily.get(key, float("-inf")), float(used))
    return [{"date": date, "used": daily[date]} for date in sorted(daily)]


def generate_candidate_curve_with_fallback(
    *,
    model: AIConfig,
    asset_type: PredictionAssetType,
    points: list[tuple[datetime, float]],
    hard_limit: float,
    approved_plans: list[dict[str, Any]],
    quality_summary: dict[str, Any] | None = None,
    forecast_start: datetime,
    baseline_curve: list[dict[str, Any]],
    completion: Callable[..., Any] = chat_completion,
) -> CandidateCurveResult:
    """Request a bounded candidate curve without sending resource identity or paths."""
    payload = {
        "asset_type": asset_type,
        "daily_capacity": _daily_capacity_points(points),
        "hard_limit": float(hard_limit),
        "quality_summary": {
            key: quality_summary[key]
            for key in (
                "status",
                "sample_count",
                "coverage_ratio",
                "data_gaps",
                "latest_observed_at",
                "forecast_fresh_at",
            )
            if quality_summary is not None and key in quality_summary
        },
        "approved_plans": [
            {
                "effective_at": str(plan["effective_at"]),
                "capacity_delta": float(plan["capacity_delta"]),
            }
            for plan in approved_plans
        ],
        "forecast_start": forecast_start.astimezone(timezone.utc).date().isoformat(),
        "forecast_days": 30,
    }
    messages = [
        {
            "role": "system",
            "content": (
                "Return only JSON with a curve array containing exactly 30 UTC daily "
                "objects: observed_at, p10, p50, p90. Do not include explanations."
            ),
        },
        {"role": "user", "content": json.dumps(payload, separators=(",", ":"))},
    ]
    try:
        response = completion(model, messages, tools=[])
        decoded = json.loads(response.text)
        raw_curve = decoded["curve"] if isinstance(decoded, dict) else decoded
        return CandidateCurveResult(
            curve=validate_ai_prediction_curve(raw_curve, forecast_start=forecast_start),
            source="ai_candidate",
        )
    except (AIClientError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        fallback_reason = (
            "timeout"
            if isinstance(error, AIClientError) and "超时" in str(error)
            else "invalid_output"
        )
        return CandidateCurveResult(
            curve=baseline_curve,
            source="baseline_fallback",
            fallback_reason=fallback_reason,
        )


def persist_candidate_prediction(
    db,
    *,
    candidate_id: int,
    asset_type: PredictionAssetType,
    asset_id: int,
    project_id: int | None,
    forecast_start: datetime,
    baseline_curve: list[dict[str, Any]],
    result: CandidateCurveResult,
) -> CapacityPredictionCandidateForecast:
    if capacityPredictionCrud.get_candidate(db, candidate_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="capacity prediction candidate was not found")
    if forecast_start.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="forecast_start must include a UTC offset")
    forecast_start = forecast_start.astimezone(timezone.utc)
    existing = capacityPredictionCrud.get_candidate_forecast(
        db,
        candidate_id=candidate_id,
        asset_type=asset_type,
        asset_id=str(asset_id),
        forecast_start=forecast_start,
    )
    if existing is not None:
        return existing
    persisted = capacityPredictionCrud.add_candidate_forecast(
        db,
        CapacityPredictionCandidateForecast(
            candidate_id=candidate_id,
            asset_type=asset_type,
            asset_id=str(asset_id),
            project_id=project_id,
            forecast_start=forecast_start,
            baseline_curve=baseline_curve,
            curve=result.curve,
            source=result.source,
            fallback_reason=result.fallback_reason,
        ),
    )
    audit_service.append_audit_event(
        db,
        context=audit_service.AuditContext(
            request_id=uuid4(),
            trace_id=uuid4(),
            operation_id=uuid4(),
            actor_type="system",
        ),
        phase="result",
        action="capacity_prediction.generate",
        resource_type="capacity_prediction",
        resource_id=persisted.id,
        project_id=project_id,
        outcome="success",
        after_summary={
            "candidate_id": candidate_id,
            "asset_type": asset_type,
            "asset_id": asset_id,
            "source": result.source,
        },
    )
    if result.source == "baseline_fallback":
        audit_service.append_audit_event(
            db,
            context=audit_service.AuditContext(
                request_id=uuid4(),
                trace_id=uuid4(),
                operation_id=uuid4(),
                actor_type="system",
            ),
            phase="result",
            action="capacity_prediction.fallback",
            resource_type="capacity_prediction",
            resource_id=persisted.id,
            project_id=project_id,
            outcome="success",
            reason_code=result.fallback_reason,
            after_summary={
                "candidate_id": candidate_id,
                "asset_type": asset_type,
                "asset_id": asset_id,
                "fallback_reason": result.fallback_reason,
            },
        )
    return persisted


def validate_ai_prediction_curve(raw_curve: list[dict[str, Any]], *, forecast_start: datetime) -> list[dict[str, Any]]:
    if len(raw_curve) != 30:
        raise ValueError("AI prediction must contain exactly 30 points")
    if forecast_start.tzinfo is None:
        raise ValueError("forecast_start must include timezone")
    expected = forecast_start.astimezone(timezone.utc).date()
    validated: list[dict[str, Any]] = []
    for offset, point in enumerate(raw_curve, start=1):
        try:
            observed_at = datetime.fromisoformat(str(point["observed_at"]).replace("Z", "+00:00"))
            p10, p50, p90 = (float(point[key]) for key in ("p10", "p50", "p90"))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("AI prediction point is invalid") from error
        if observed_at.tzinfo is None or observed_at.astimezone(timezone.utc).date() != expected + timedelta(days=offset):
            raise ValueError("AI prediction dates must be contiguous")
        if not all(math.isfinite(value) for value in (p10, p50, p90)):
            raise ValueError("AI prediction quantiles must be finite")
        if p10 < 0 or p50 < 0 or p90 < 0 or not p10 <= p50 <= p90:
            raise ValueError("AI prediction quantile order is invalid")
        validated.append({"observed_at": observed_at.astimezone(timezone.utc).isoformat(), "p10": p10, "p50": p50, "p90": p90})
    return validated


def _daily_maxima(points: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    daily: dict[datetime.date, float] = {}
    for observed_at, used in points:
        if observed_at.tzinfo is None:
            continue
        day = observed_at.astimezone(timezone.utc).date()
        daily[day] = max(daily.get(day, float("-inf")), float(used))
    return [
        (datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc), daily[day])
        for day in sorted(daily)
    ]


def _curve_mape(curve: list[dict[str, Any]], actuals: list[tuple[datetime, float]]) -> float | None:
    predicted = {
        datetime.fromisoformat(str(point["observed_at"]).replace("Z", "+00:00")).astimezone(timezone.utc).date(): float(point["p50"])
        for point in curve
    }
    errors = [
        abs((predicted[observed_at.date()] - actual) / actual) * 100
        for observed_at, actual in actuals
        if actual > 0 and observed_at.date() in predicted
    ]
    return round(sum(errors) / len(errors), 4) if errors else None


def rolling_candidate_evaluations(
    *,
    model: AIConfig,
    asset_ref,
    points: list[tuple[datetime, float]],
    hard_limit: float,
    approved_plans: list[dict[str, Any]],
    quality_summary: dict[str, Any] | None = None,
    completion: Callable[..., Any] = chat_completion,
) -> list[dict[str, Any]]:
    """Evaluate a candidate over three bounded rolling 30-day holdouts."""
    ordered = _daily_maxima(points)
    window_days = 30
    training_days = forecastIncidentService.FORECAST_TRAINING_DAYS
    if len(ordered) < training_days + window_days * 3:
        return []

    evaluations: list[dict[str, Any]] = []
    for rolling_offset in range(3, 0, -1):
        holdout_end = len(ordered) - (rolling_offset - 1) * window_days
        holdout_start = holdout_end - window_days
        training_start = holdout_start - training_days
        training = ordered[training_start:holdout_start]
        actuals = ordered[holdout_start:holdout_end]
        baseline = forecastIncidentService.build_capacity_forecast(
            asset_ref,
            points=training,
            hard_limit=hard_limit,
            now=training[-1][0],
        )
        if baseline.status != "ready":
            continue
        baseline_curve = [point.model_dump(mode="json") for point in baseline.curve]
        candidate = generate_candidate_curve_with_fallback(
            model=model,
            asset_type=asset_ref.asset_type,
            points=training,
            hard_limit=hard_limit,
            approved_plans=approved_plans,
            quality_summary={
                **(quality_summary or {}),
                "sample_count": len(training),
                "coverage_ratio": round(len(training) / training_days, 4),
                "status": "ready",
            },
            forecast_start=training[-1][0],
            baseline_curve=baseline_curve,
            completion=completion,
        )
        baseline_mape = _curve_mape(baseline_curve, actuals)
        candidate_mape = _curve_mape(candidate.curve, actuals)
        if baseline_mape is None or candidate_mape is None:
            continue
        actual_risk = any(value >= hard_limit for _observed_at, value in actuals)
        baseline_risk = any(float(point["p90"]) >= hard_limit for point in baseline_curve)
        candidate_risk = any(float(point["p90"]) >= hard_limit for point in candidate.curve)
        evaluations.append(
            {
                "window_start": actuals[0][0],
                "window_end": actuals[-1][0] + timedelta(days=1),
                "baseline_mape": baseline_mape,
                "candidate_mape": candidate_mape,
                "risk_coverage_ok": not (actual_risk and baseline_risk and not candidate_risk),
            }
        )
    return evaluations


def candidate_meets_activation_gate(evaluations: list[dict[str, Any]]) -> bool:
    if len(evaluations) < 3:
        return False
    try:
        windows = [(item["window_start"], item["window_end"]) for item in evaluations]
        if len(set(windows)) != len(windows):
            return False
        recent = sorted(evaluations, key=lambda item: item["window_end"])[-3:]
    except (KeyError, TypeError):
        return False
    if not all(bool(item.get("risk_coverage_ok")) for item in recent):
        return False
    try:
        baseline = sum(float(item["baseline_mape"]) for item in recent) / 3
        candidate = sum(float(item["candidate_mape"]) for item in recent) / 3
    except (KeyError, TypeError, ValueError):
        return False
    return baseline > 0 and candidate <= baseline * 0.90


def candidate_governance_view(db, candidate: CapacityPredictionCandidate) -> dict[str, Any]:
    """Return aggregate evaluation evidence only; resource identities stay private."""
    model = db.get(AIConfig, candidate.ai_model_id)
    evaluations = capacityPredictionCrud.list_candidate_evaluations(db, candidate_id=candidate.id)
    rows = [
        {
            "baseline_mape": item.baseline_mape,
            "candidate_mape": item.candidate_mape,
            "risk_coverage_ok": item.risk_coverage_ok,
            "window_start": item.window_start,
            "window_end": item.window_end,
            "created_at": item.created_at,
        }
        for item in evaluations
    ]
    forecast_summary = capacityPredictionCrud.candidate_forecast_summary(db, candidate_id=candidate.id)
    return {
        "id": candidate.id,
        "version": candidate.version,
        "ai_model_id": candidate.ai_model_id,
        "ai_model_name": model.name if model is not None else None,
        "enabled": candidate.enabled,
        "created_at": candidate.created_at,
        "evaluations": rows,
        "activation_ready": candidate_meets_activation_gate(rows),
        **forecast_summary,
    }


def _resource(db, *, current_user, asset_type: PredictionAssetType, asset_id: int, minimum_role: str):
    if asset_type == "storage_cluster":
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
        if not is_super_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super admin permission required")
        cluster = db.get(StorageCluster, asset_id)
        if cluster is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="storage cluster was not found")
        return cluster, None
    if asset_type == "project":
        project_access_service.require_project_permission(db, current_user, asset_id, minimum_role)
        return db.get(Project, asset_id), asset_id
    if asset_type == "group":
        group = project_access_service.require_group_permission(db, current_user, asset_id, minimum_role)
        return group, group.project_id
    usage = project_access_service.require_storage_usage_permission(db, current_user, asset_id, minimum_role)
    if usage.group is None:
        if not is_super_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project permission required")
        return usage, None
    return usage, usage.group.project_id


def _risk_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_exhaustion_risk_summary(forecast, *, now: datetime | None = None) -> dict[str, Any]:
    """Return the single server-authoritative 30-day exhaustion-risk conclusion."""
    now = (now or utc_now()).astimezone(timezone.utc)
    quality_status = (forecast.input_quality or {}).get("status")
    exhaustion_dates = forecast.exhaustion_dates or {}
    p50 = _risk_datetime(exhaustion_dates.get("p50"))
    p90 = _risk_datetime(exhaustion_dates.get("p90"))
    if quality_status != "ready":
        level = "insufficient"
        reason = "有效日少于 30 天或覆盖率低于 80%"
    elif p90 is not None and p90 <= now + timedelta(days=7):
        level = "critical"
        reason = "P90 预计在 7 日内达到硬限额"
    elif p50 is not None and p50 <= now + timedelta(days=30):
        level = "high"
        reason = "P50 预计在 30 日内达到硬限额"
    elif p90 is not None and p90 <= now + timedelta(days=30):
        level = "watch"
        reason = "P90 预计在 30 日内达到硬限额"
    else:
        level = "none"
        reason = "P50 和 P90 均未在未来 30 日内达到硬限额"
    return {
        "level": level,
        "label": RISK_LABELS[level],
        "p50_exhaustion_at": p50,
        "p90_exhaustion_at": p90,
        "horizon_days": 30,
        "reason": reason,
        "generated_at": forecast.created_at,
    }


def prediction_visible_to_user(db, *, current_user) -> bool:
    if current_user is None:
        return False
    if is_super_admin(current_user):
        return True
    settings = capacityPredictionCrud.get_settings(db)
    return settings is not None and settings.user_visible is True


def get_prediction_settings(db) -> bool:
    settings = capacityPredictionCrud.get_settings(db)
    return settings is not None and settings.user_visible is True


def update_prediction_settings(db, *, user_id: int, user_visible: bool):
    settings = capacityPredictionCrud.get_or_create_settings(db)
    settings.user_visible = user_visible
    settings.updated_by = user_id
    db.flush()
    return settings


def list_candidate_governance(db) -> list[dict[str, Any]]:
    return [
        candidate_governance_view(db, item)
        for item in capacityPredictionCrud.list_candidates(db)
    ]


def _require_prediction_visibility(db, *, current_user) -> None:
    if not prediction_visible_to_user(db, current_user=current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="capacity prediction is globally disabled")


def _exhaustion_dates(curve: list[dict[str, Any]], hard_limit: float) -> dict[str, str | None]:
    return {
        quantile: next(
            (
                str(point["observed_at"])
                for point in curve
                if float(point[quantile]) >= hard_limit
            ),
            None,
        )
        for quantile in ("p10", "p50", "p90")
    }


def _prediction_view(baseline, candidate_forecast, candidate):
    if candidate_forecast is None:
        return baseline
    quality = dict(baseline.input_quality or {})
    quality.update(
        {
            "prediction_source": candidate_forecast.source,
            "fallback_reason": candidate_forecast.fallback_reason,
            "candidate_version": candidate.version if candidate is not None else None,
        }
    )
    values = {
        field: getattr(baseline, field)
        for field in (
            "id", "asset_type", "asset_id", "storage_cluster_id", "project_id", "vendor",
            "display_name", "training_start", "training_end", "hard_limit", "algorithm_version",
            "backtest_mape", "created_at",
        )
    }
    values.update(
        {
            "curve": candidate_forecast.curve,
            "exhaustion_dates": _exhaustion_dates(candidate_forecast.curve, baseline.hard_limit),
            "input_quality": quality,
        }
    )
    return SimpleNamespace(**values)


def get_resource_prediction(db, *, current_user, asset_type: PredictionAssetType, asset_id: int):
    _resource(db, current_user=current_user, asset_type=asset_type, asset_id=asset_id, minimum_role="reader")
    _require_prediction_visibility(db, current_user=current_user)
    forecast = capacityPredictionCrud.latest_forecast(db, asset_type=asset_type, asset_id=str(asset_id))
    if forecast is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="capacity prediction was not found")
    candidate_forecast = capacityPredictionCrud.latest_active_candidate_forecast(
        db,
        asset_type=asset_type,
        asset_id=str(asset_id),
        forecast_start=forecast.training_end,
    )
    candidate = (
        capacityPredictionCrud.get_candidate(db, candidate_forecast.candidate_id)
        if candidate_forecast is not None
        else None
    )
    return _prediction_view(forecast, candidate_forecast, candidate)


def get_capacity_exhaustion_risk(
    db,
    *,
    current_user,
    asset_type: PredictionAssetType,
    asset_id: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    forecast = get_resource_prediction(
        db,
        current_user=current_user,
        asset_type=asset_type,
        asset_id=asset_id,
    )
    return build_exhaustion_risk_summary(forecast, now=now)


def list_final_predictions(db, *, current_user, page: int, size: int):
    _require_prediction_visibility(db, current_user=current_user)
    forecasts, total = capacityPredictionCrud.list_latest_forecasts(
        db,
        visible_project_ids=forecastIncidentService.visible_project_ids(db, current_user),
        page=page,
        size=size,
    )
    candidate = capacityPredictionCrud.active_candidate(db)
    if candidate is None or not forecasts:
        return forecasts, total
    candidate_forecasts = capacityPredictionCrud.list_candidate_forecasts_for_baselines(
        db,
        candidate_id=candidate.id,
        baseline_keys=[
            (forecast.asset_type, forecast.asset_id, forecast.training_end)
            for forecast in forecasts
        ],
    )
    candidate_by_asset = {
        (item.asset_type, item.asset_id, item.forecast_start): item
        for item in candidate_forecasts
    }
    return [
        _prediction_view(
            forecast,
            candidate_by_asset.get((forecast.asset_type, forecast.asset_id, forecast.training_end)),
            candidate,
        )
        for forecast in forecasts
    ], total


def list_resource_capacity_plans(db, *, current_user, asset_type: PredictionAssetType, asset_id: int):
    _resource(db, current_user=current_user, asset_type=asset_type, asset_id=asset_id, minimum_role="reader")
    _require_prediction_visibility(db, current_user=current_user)
    return capacityPredictionCrud.list_plans(db, asset_type=asset_type, asset_id=str(asset_id))


def list_resource_related_incidents(db, *, current_user, asset_type: PredictionAssetType, asset_id: int) -> list[dict[str, Any]]:
    _resource(db, current_user=current_user, asset_type=asset_type, asset_id=asset_id, minimum_role="reader")
    result = []
    for incident in forecastIncidentCrud.list_resource_incidents(
        db,
        asset_type=asset_type,
        asset_id=str(asset_id),
    ):
        diagnosis = forecastIncidentCrud.latest_diagnosis(db, incident.id)
        result.append(
            {
                "id": incident.id,
                "category": incident.category,
                "severity": incident.severity,
                "status": incident.status,
                "updated_at": incident.updated_at,
                "rca_confidence": diagnosis.confidence if diagnosis is not None else None,
            }
        )
    return result


def resource_prediction_access(db, *, current_user, asset_type: PredictionAssetType, asset_id: int) -> dict[str, bool]:
    _resource(db, current_user=current_user, asset_type=asset_type, asset_id=asset_id, minimum_role="reader")
    _require_prediction_visibility(db, current_user=current_user)
    try:
        _resource(db, current_user=current_user, asset_type=asset_type, asset_id=asset_id, minimum_role="project_admin")
    except HTTPException as error:
        if error.status_code != status.HTTP_403_FORBIDDEN:
            raise
        return {"visible": True, "can_manage_plans": False}
    return {"visible": True, "can_manage_plans": True}


def create_capacity_plan(
    db, *, current_user, asset_type: PredictionAssetType, asset_id: int,
    effective_at: datetime, capacity_delta: float, reason: str,
):
    if effective_at.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="effective_at must include a UTC offset")
    _resource_obj, project_id = _resource(
        db, current_user=current_user, asset_type=asset_type, asset_id=asset_id, minimum_role="project_admin"
    )
    _require_prediction_visibility(db, current_user=current_user)
    if project_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project-scoped resource required")
    return capacityPredictionCrud.add_plan(
        db,
        CapacityPredictionPlan(
            asset_type=asset_type, asset_id=str(asset_id), project_id=project_id,
            effective_at=effective_at.astimezone(timezone.utc), capacity_delta=capacity_delta,
            reason=reason, created_by=current_user.id,
        ),
    )


def create_capacity_prediction_candidate(db, *, version: str, ai_model_id: int) -> CapacityPredictionCandidate:
    if capacityPredictionCrud.get_candidate_by_version(db, version) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="capacity prediction version already exists")
    model = db.get(AIConfig, ai_model_id)
    if model is None or model.enabled is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="configured and enabled AI model is required",
        )
    try:
        return capacityPredictionCrud.add_candidate(
            db,
            CapacityPredictionCandidate(version=version, ai_model_id=ai_model_id, enabled=False),
        )
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="capacity prediction version already exists",
        ) from error


def record_capacity_prediction_evaluation(
    db,
    *,
    candidate_id: int,
    baseline_mape: float,
    candidate_mape: float,
    risk_coverage_ok: bool,
    window_start: datetime,
    window_end: datetime,
) -> CapacityPredictionEvaluation:
    if capacityPredictionCrud.get_candidate(db, candidate_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="capacity prediction candidate was not found")
    if window_start.tzinfo is None or window_end.tzinfo is None or window_start >= window_end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="evaluation window is invalid")
    if window_end.astimezone(timezone.utc) - window_start.astimezone(timezone.utc) != timedelta(days=30):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="evaluation window must be exactly 30-day holdout",
        )
    if not math.isfinite(baseline_mape) or not math.isfinite(candidate_mape):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="MAPE must be finite")
    if baseline_mape < 0 or candidate_mape < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="MAPE must not be negative")
    window_start = window_start.astimezone(timezone.utc)
    window_end = window_end.astimezone(timezone.utc)
    if capacityPredictionCrud.has_candidate_evaluation(
        db,
        candidate_id=candidate_id,
        window_start=window_start,
        window_end=window_end,
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="candidate evaluation window already exists")
    try:
        return capacityPredictionCrud.add_candidate_evaluation(
            db,
            CapacityPredictionEvaluation(
                candidate_id=candidate_id,
                baseline_mape=baseline_mape,
                candidate_mape=candidate_mape,
                risk_coverage_ok=risk_coverage_ok,
                window_start=window_start,
                window_end=window_end,
            ),
        )
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="candidate evaluation window already exists",
        ) from error


def activate_capacity_prediction_candidate(db, *, candidate_id: int) -> CapacityPredictionCandidate:
    candidate = capacityPredictionCrud.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="capacity prediction candidate was not found")
    model = db.get(AIConfig, candidate.ai_model_id)
    if model is None or model.enabled is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="configured and enabled AI model is required",
        )
    evaluations = capacityPredictionCrud.list_candidate_evaluations(db, candidate_id=candidate_id)
    evaluation_rows = [
        {
            "baseline_mape": item.baseline_mape,
            "candidate_mape": item.candidate_mape,
            "risk_coverage_ok": item.risk_coverage_ok,
            "window_start": item.window_start,
            "window_end": item.window_end,
        }
        for item in evaluations
    ]
    if not candidate_meets_activation_gate(evaluation_rows):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="candidate activation gate was not met")
    capacityPredictionCrud.disable_candidates(db)
    candidate.enabled = True
    db.add(candidate)
    db.flush()
    return candidate
