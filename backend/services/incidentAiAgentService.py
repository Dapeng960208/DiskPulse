# -*- coding: utf-8 -*-
"""Schema and execution boundary for the background Incident AI agent."""
from datetime import datetime, timezone
import json
import math
from typing import Any, Callable, Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError

from crud import incidentAiAgentCrud
from models import IncidentAiRun, IncidentTimeline
from services.ai_client import AIClientError, chat_completion


IncidentAiClassification = Literal["actionable", "normal_fluctuation", "insufficient_evidence"]
IncidentAiUrgency = Literal["low", "medium", "high", "critical"]
IncidentAiConfidence = Literal["low", "medium", "high"]
IncidentStatus = Literal["open", "acknowledged", "investigating", "mitigated", "resolved"]


class IncidentAiAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    classification: IncidentAiClassification
    urgency: IncidentAiUrgency
    confidence: IncidentAiConfidence
    summary: str = Field(min_length=1, max_length=2000)
    evidence_basis: list[str] = Field(default_factory=list, max_length=8)
    investigation_steps: list[str] = Field(default_factory=list, max_length=8)
    resolution_steps: list[str] = Field(default_factory=list, max_length=8)
    proposed_next_status: IncidentStatus | None = None
    transition_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_classification_requirements(self):
        if self.classification == "normal_fluctuation" and not self.evidence_basis:
            raise ValueError("normal_fluctuation 必须提供低负载、短时波动或证据不足的依据")
        if self.classification == "actionable" and (
            not self.investigation_steps or not self.resolution_steps
        ):
            raise ValueError("actionable 必须提供排查步骤和解决建议")
        return self


def validate_agent_assessment(assessment: IncidentAiAssessment, *, current_status: str) -> IncidentAiAssessment:
    """Allow the agent to keep state or take exactly one existing state-machine step."""
    if assessment.proposed_next_status in (None, current_status):
        return assessment
    from services.forecastIncidentService import can_transition_incident

    if not can_transition_incident(current_status, assessment.proposed_next_status):
        raise ValueError("AI 建议的状态必须是当前状态的相邻下一步")
    return assessment


def calibrated_ai_urgency(assessment: IncidentAiAssessment) -> tuple[IncidentAiUrgency, bool]:
    """Apply the conservative urgency floor without changing deterministic severity."""
    if assessment.confidence != "low":
        return assessment.urgency, False
    downgrade = {"critical": "high", "high": "medium", "medium": "low", "low": "low"}
    urgency = downgrade[assessment.urgency]
    return urgency, urgency != assessment.urgency


def update_settings(
    db,
    *,
    actor_id: int | None,
    enabled: bool,
    model_ids: list[int],
    iops_absolute_floor: float,
    iops_baseline_ratio: float,
):
    if not math.isfinite(iops_absolute_floor) or iops_absolute_floor < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="IOPS 绝对下限无效")
    if not math.isfinite(iops_baseline_ratio) or not 0 <= iops_baseline_ratio <= 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="IOPS 基线比例无效")
    normalized_ids = [int(model_id) for model_id in model_ids]
    if len(normalized_ids) != len(set(normalized_ids)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="AI 模型不能重复选择")
    if enabled and not normalized_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="启用 AI 时必须选择至少一个模型")
    models = incidentAiAgentCrud.list_models_by_ids(db, normalized_ids)
    by_id = {model.id: model for model in models}
    if any(model_id not in by_id or not by_id[model_id].enabled for model_id in normalized_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="只能选择已启用的 AI 模型")
    settings = incidentAiAgentCrud.get_or_create_settings(db)
    settings.enabled = bool(enabled)
    settings.iops_absolute_floor = float(iops_absolute_floor)
    settings.iops_baseline_ratio = float(iops_baseline_ratio)
    settings.updated_by = actor_id
    incidentAiAgentCrud.replace_model_bindings(db, settings=settings, model_ids=normalized_ids)
    db.commit()
    db.refresh(settings)
    return settings


def get_settings(db):
    return incidentAiAgentCrud.get_or_create_settings(db)


def settings_out(db, settings) -> dict:
    selected_models = [binding.ai_model for binding in settings.model_bindings if binding.ai_model is not None]
    available_models = incidentAiAgentCrud.list_enabled_models(db)
    def model_out(model):
        return {"id": model.id, "name": model.name, "provider": model.provider, "model": model.model}
    return {
        "enabled": settings.enabled,
        "model_ids": [binding.ai_model_id for binding in settings.model_bindings],
        "models": [model_out(model) for model in selected_models],
        "available_models": [model_out(model) for model in available_models],
        "iops_absolute_floor": float(settings.iops_absolute_floor),
        "iops_baseline_ratio": float(settings.iops_baseline_ratio),
        "updated_at": settings.updated_at,
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_snapshot(db, incident) -> dict[str, Any]:
    from crud import forecastIncidentCrud
    from services import forecastIncidentService

    diagnosis = forecastIncidentCrud.latest_diagnosis(db, incident.id)
    evidence = forecastIncidentCrud.list_incident_evidence(db, incident.id)
    anomaly_context = forecastIncidentService.build_anomaly_evidence_context(db, evidence)

    def safe_number(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def safe_integer(value, *, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return minimum
        return max(minimum, min(maximum, number))

    def safe_history(value):
        if not isinstance(value, dict):
            return {"sample_count": 0, "coverage_ratio": 0.0}
        result = {
            "sample_count": safe_integer(value.get("sample_count"), minimum=0, maximum=100_000),
            "coverage_ratio": max(0.0, min(1.0, safe_number(value.get("coverage_ratio")) or 0.0)),
        }
        for key in ("median", "p95", "mad"):
            number = safe_number(value.get(key))
            if number is not None:
                result[key] = number
        return result

    performance_context = []
    for observation in anomaly_context.values():
        value = (observation.input_quality or {}).get("ai_performance_context")
        if not isinstance(value, dict):
            continue
        trend = []
        for point in (value.get("trend_2h_p95") or [])[-24:]:
            if not isinstance(point, dict):
                continue
            measured = safe_number(point.get("p95"))
            if measured is not None:
                trend.append({
                    "minutes_before_trigger": safe_integer(point.get("minutes_before_trigger"), minimum=0, maximum=120),
                    "p95": measured,
                })
        associated_metrics = []
        for metric in (value.get("associated_metrics") or [])[:3]:
            if not isinstance(metric, dict) or metric.get("metric") not in {"latency", "iops", "throughput"}:
                continue
            latest = safe_number(metric.get("latest_p95"))
            if latest is not None:
                associated_metrics.append({
                    "metric": metric["metric"],
                    "latest_p95": latest,
                    "history_28d": safe_history(metric.get("history_28d")),
                })
        performance_context.append({
            "metric": value.get("metric") if value.get("metric") in {"latency", "iops", "throughput"} else "unknown",
            "trigger_three_bucket_p95": [
                number for number in (safe_number(item) for item in (value.get("trigger_three_bucket_p95") or [])[:3])
                if number is not None
            ],
            "trend_2h_p95": trend,
            "history_28d": safe_history(value.get("history_28d")),
            "associated_metrics": associated_metrics,
        })
    return {
        "category": incident.category,
        "severity": incident.severity,
        "status": incident.status,
        "opened_at": incident.opened_at.isoformat(),
        "last_evidence_at": incident.last_evidence_at.isoformat(),
        "diagnosis": (
            {
                "confidence": diagnosis.confidence,
                "candidates": [
                    {
                        "category": item.get("category"),
                        "score": item.get("score"),
                        "evidence_count": len(item.get("evidence_refs") or []),
                        "data_gaps": item.get("data_gaps") or [],
                    }
                    for item in diagnosis.candidates or []
                    if isinstance(item, dict)
                ],
                "data_gaps": diagnosis.data_gaps,
            }
            if diagnosis is not None
            else None
        ),
        "evidence": [
            {
                "source": item.source,
                "type": item.evidence_type,
                "observed_at": item.observed_at.isoformat(),
                "data_gaps": list(item.data_gaps or []),
            }
            for item in evidence[-20:]
        ],
        "performance_context": performance_context[:6],
    }


def _messages(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是 DiskPulse 事件处置 Agent。仅依据提供的脱敏事件事实判断，"
                "不得虚构设备操作、凭据、路径或未给出的证据。"
                "仅返回 JSON：classification(actionable|normal_fluctuation|insufficient_evidence)、"
                "urgency(low|medium|high|critical)、confidence(low|medium|high)、summary、investigation_steps、resolution_steps、"
                "evidence_basis、proposed_next_status、transition_reason。"
                "normal_fluctuation 的 evidence_basis 必须明确低绝对负载、短时波动或证据不足；"
                "actionable 必须包含至少一项排查步骤和一项解决建议。"
                "状态只能保持不变或推进一个相邻步骤；解决方案只能是建议和验证步骤，不能执行写操作。"
            ),
        },
        {"role": "user", "content": json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))},
    ]


def _comment(
    assessment: IncidentAiAssessment,
    *,
    effective_urgency: IncidentAiUrgency,
    urgency_downgraded: bool,
) -> str:
    sections = [
        f"AI 研判（紧急度：{effective_urgency}，置信度：{assessment.confidence}）：{assessment.summary}",
        "研判依据：" + ("；".join(assessment.evidence_basis) or "当前关联证据不足以形成更多依据。"),
        "排查建议：" + ("；".join(assessment.investigation_steps) or "继续依据关联证据观察。"),
        "解决建议：" + ("；".join(assessment.resolution_steps) or "当前无需设备写操作。"),
    ]
    if urgency_downgraded:
        sections.append("低置信度已将 AI 紧急度降一级；确定性事件严重度未改变。")
    if assessment.transition_reason:
        sections.append(f"状态建议：{assessment.transition_reason}")
    return "\n".join(sections)[:2000]


def review_incident(
    db,
    *,
    incident_id: int,
    trigger: str,
    idempotency_key: str,
    completion: Callable[..., Any] = chat_completion,
) -> IncidentAiRun | None:
    """Generate and persist one bounded AI assessment without device-side effects."""
    from crud import forecastIncidentCrud
    from services import forecastIncidentService

    settings = get_settings(db)
    if not settings.enabled or not settings.model_bindings:
        return None
    incident = forecastIncidentCrud.get_incident(db, incident_id)
    if incident is None or incident.status == "resolved":
        return None
    existing = incidentAiAgentCrud.get_run_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        return existing
    snapshot = _safe_snapshot(db, incident)
    try:
        run = incidentAiAgentCrud.add_run(
            db,
            IncidentAiRun(
                incident_id=incident.id,
                trigger=trigger,
                idempotency_key=idempotency_key,
                status="running",
                input_snapshot=snapshot,
                attempt_summary=[],
            ),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        return incidentAiAgentCrud.get_run_by_idempotency_key(db, idempotency_key)
    assessment: IncidentAiAssessment | None = None
    selected_model = None
    attempts: list[dict[str, Any]] = []
    for binding in settings.model_bindings:
        model = binding.ai_model
        if model is None or not model.enabled:
            attempts.append({"model_id": binding.ai_model_id, "outcome": "skipped"})
            continue
        try:
            result = completion(model, _messages(snapshot), tools=[])
            decoded = json.loads(result.text)
            candidate = validate_agent_assessment(IncidentAiAssessment.model_validate(decoded), current_status=snapshot["status"])
        except (AIClientError, ValueError, TypeError, json.JSONDecodeError):
            attempts.append({"model_id": model.id, "outcome": "failed"})
            continue
        except Exception:
            attempts.append({"model_id": model.id, "outcome": "failed"})
            continue
        assessment = candidate
        selected_model = model
        attempts.append({"model_id": model.id, "outcome": "succeeded"})
        break
    db.rollback()
    run = incidentAiAgentCrud.get_run_by_idempotency_key(db, idempotency_key)
    current = forecastIncidentCrud.get_incident(db, incident_id)
    if run is None or current is None:
        return run
    run.attempt_summary = attempts
    if assessment is None or selected_model is None:
        run.status = "failed"
        run.error_code = "all_models_failed"
        run.completed_at = _utc_now()
        db.commit()
        return run
    if current.status != snapshot["status"] or current.last_evidence_at.isoformat() != snapshot["last_evidence_at"]:
        run.status = "superseded"
        run.completed_at = _utc_now()
        db.commit()
        return run
    refreshed_settings = get_settings(db)
    if not refreshed_settings.enabled:
        run.status = "skipped"
        run.error_code = "disabled"
        run.completed_at = _utc_now()
        db.commit()
        return run
    effective_urgency, urgency_downgraded = calibrated_ai_urgency(assessment)
    analyzed_at = _utc_now()
    payload = assessment.model_dump(mode="json")
    payload.update({
        "model_name": selected_model.name,
        "analyzed_at": analyzed_at.isoformat(),
        "model_urgency": assessment.urgency,
        "urgency": effective_urgency,
        "urgency_downgraded": urgency_downgraded,
    })
    current.ai_urgency = effective_urgency
    current.ai_urgency_reason = assessment.summary
    current.ai_assessment = payload
    current.ai_analyzed_at = analyzed_at
    db.add(
        IncidentTimeline(
            incident_id=current.id,
            event_type="ai_analysis",
            comment=_comment(
                assessment,
                effective_urgency=effective_urgency,
                urgency_downgraded=urgency_downgraded,
            ),
        )
    )
    if assessment.proposed_next_status not in (None, current.status):
        forecastIncidentService.require_incident_transition(current.status, assessment.proposed_next_status)
        previous_status = current.status
        current.status = assessment.proposed_next_status
        current.resolved_at = analyzed_at if current.status == "resolved" else None
        db.add(
            IncidentTimeline(
                incident_id=current.id,
                event_type="ai_status_changed",
                from_status=previous_status,
                to_status=current.status,
                comment=assessment.transition_reason,
            )
        )
    run.status = "succeeded"
    run.model_id = selected_model.id
    run.model_snapshot = {"name": selected_model.name, "provider": selected_model.provider, "model": selected_model.model}
    run.assessment = payload
    run.completed_at = analyzed_at
    db.commit()
    return run
