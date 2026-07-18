# -*- coding: utf-8 -*-
"""Server-side guardrail for AI narration of deterministic Incident diagnoses."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RestrictedDiagnosisRender:
    text: str
    used_fallback: bool


def _canonical_payload(diagnosis: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        {
            "category": item.get("category"),
            "score": item.get("score"),
            "evidence_ids": sorted(item.get("evidence_refs") or item.get("evidence_ids") or []),
            "data_gaps": sorted(item.get("data_gaps") or []),
        }
        for item in diagnosis.get("candidates") or []
    ]
    return {
        "incident_id": diagnosis.get("incident_id"),
        "confidence": diagnosis.get("confidence"),
        "candidates": candidates,
        "evidence_ids": sorted(diagnosis.get("evidence_ids") or []),
        "data_gaps": sorted(diagnosis.get("data_gaps") or []),
    }


def _deterministic_template(diagnosis: dict[str, Any]) -> str:
    payload = _canonical_payload(diagnosis)
    candidates = payload["candidates"]
    if not candidates:
        gaps = "、".join(payload["data_gaps"]) or "暂无可用证据"
        return f"事件 {payload['incident_id']} 当前证据不足；数据缺口：{gaps}。"
    rendered = []
    for item in candidates[:3]:
        references = "、".join(item["evidence_ids"]) or "无"
        gaps = "、".join(item["data_gaps"]) or "无"
        rendered.append(
            f"{item['category']}（分数 {item['score']}；证据 {references}；数据缺口 {gaps}）"
        )
    return (
        f"事件 {payload['incident_id']} 的确定性诊断（置信度 {payload['confidence']}）："
        + "；".join(rendered)
        + "。"
    )


def _model_payload_matches(model_text: str, diagnosis: dict[str, Any]) -> bool:
    """Accept only an exact, schema-limited echo of deterministic facts.

    The model is not trusted to narrate arbitrary free text: unknown evidence,
    candidate, score, confidence or data-gap fields make the response invalid.
    The user-visible wording is always rendered from the deterministic payload.
    """
    try:
        candidate = json.loads(model_text)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(candidate, dict):
        return False
    allowed = _canonical_payload(diagnosis)
    return _canonical_payload(candidate) == allowed


def render_restricted_diagnosis(
    *, model_text: str, diagnosis: dict[str, Any]
) -> RestrictedDiagnosisRender:
    """Return a safe narration; reject additions and fall back deterministically."""
    return RestrictedDiagnosisRender(
        text=_deterministic_template(diagnosis),
        used_fallback=not _model_payload_matches(model_text, diagnosis),
    )
