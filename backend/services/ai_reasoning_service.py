# -*- coding: utf-8 -*-
"""Provider-native reasoning capability discovery and validation."""

from __future__ import annotations

import json
from typing import Any


_AUTO_ONLY = {
    "kind": "none",
    "options": ["auto"],
    "provider_default": None,
    "mandatory": False,
}

_OPENAI_CHAT_EFFORTS = {
    "gpt-5": ["minimal", "low", "medium", "high"],
    "gpt-5-2025-08-07": ["minimal", "low", "medium", "high"],
    "gpt-5-mini": ["minimal", "low", "medium", "high"],
    "gpt-5-mini-2025-08-07": ["minimal", "low", "medium", "high"],
    "gpt-5-nano": ["minimal", "low", "medium", "high"],
    "gpt-5-nano-2025-08-07": ["minimal", "low", "medium", "high"],
    "gpt-5.1": ["none", "low", "medium", "high"],
    "gpt-5.1-2025-11-13": ["none", "low", "medium", "high"],
    "gpt-5.2": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.2-2025-12-11": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.4": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.4-2026-03-05": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.4-mini": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.4-mini-2026-03-17": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.4-nano": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.4-nano-2026-03-17": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.5": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.5-2026-04-23": ["none", "low", "medium", "high", "xhigh"],
    "gpt-5.6": ["none", "low", "medium", "high", "xhigh", "max"],
    "gpt-5.6-sol": ["none", "low", "medium", "high", "xhigh", "max"],
    "gpt-5.6-terra": ["none", "low", "medium", "high", "xhigh", "max"],
    "gpt-5.6-luna": ["none", "low", "medium", "high", "xhigh", "max"],
}


def _control(
    kind: str,
    options: list[str],
    *,
    provider_default: str | None = None,
    mandatory: bool = False,
    source: str = "official_catalog",
    status: str = "ready",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "options": list(dict.fromkeys(["auto", *options])),
        "provider_default": provider_default,
        "mandatory": bool(mandatory),
        "source": source,
        "status": status,
    }


def _dynamic_control(provider: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
    if provider == "openrouter":
        effort = metadata.get("reasoning") or {}
        options = effort.get("supported_efforts") or []
        if options:
            return _control(
                "effort",
                [str(item) for item in options],
                provider_default=effort.get("default_effort"),
                mandatory=bool(effort.get("mandatory", False)),
                source="provider",
            )
    if provider == "claude":
        effort = (metadata.get("capabilities") or {}).get("effort") or {}
        options = effort.get("supported_efforts") or effort.get("levels") or []
        if options:
            return _control(
                "effort",
                [str(item) for item in options],
                provider_default=effort.get("default_effort"),
                source="provider",
            )
    return None


def resolve_reasoning_control(
    provider: str,
    model_name: str,
    *,
    provider_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if provider_metadata:
        dynamic = _dynamic_control(provider, provider_metadata)
        if dynamic is not None:
            return dynamic

    model = model_name.strip().lower()
    if provider == "openai" and model in _OPENAI_CHAT_EFFORTS:
        return _control(
            "effort",
            _OPENAI_CHAT_EFFORTS[model],
            provider_default="medium",
        )
    if provider == "ollama" and model.startswith("gpt-oss"):
        return _control("effort", ["low", "medium", "high"], provider_default="medium")
    if provider == "ollama" and any(name in model for name in ("thinking", "deepseek-r1", "qwq")):
        return _control("toggle", ["off", "on"], provider_default="on")
    if provider == "deepseek" and model in {
        "deepseek-reasoner",
        "deepseek-chat",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
    }:
        return _control("effort", ["high", "max"], provider_default="high")
    if provider == "dashscope" and any(name in model for name in ("qwen3", "qwq")):
        return _control("toggle", ["off", "on"], provider_default="on")
    if provider == "volcengine" and any(name in model for name in ("thinking", "seed")):
        return _control("toggle", ["off", "on"], provider_default="on")
    if provider == "zhipu" and model.startswith("glm-5"):
        return _control(
            "effort",
            ["minimal", "low", "medium", "high", "xhigh"],
            provider_default="high",
        )
    if provider == "zhipu" and model.startswith("glm-"):
        return _control("toggle", ["off", "on"], provider_default="on")
    if provider == "moonshot" and model.startswith("kimi-k3"):
        return _control("effort", ["low", "high", "max"], provider_default="max")
    if provider == "moonshot" and ("thinking" in model or model.startswith("kimi-k2")):
        return _control("toggle", ["off", "on"], provider_default="on")
    if provider == "qianfan" and model.startswith(
        ("deepseek-v4-pro", "deepseek-v4-flash")
    ):
        return _control("effort", ["high", "max"], provider_default="high")
    if provider == "qianfan" and model.startswith("gpt-oss"):
        return _control(
            "effort",
            ["low", "medium", "high"],
            provider_default="medium",
        )
    if provider == "qianfan" and (
        model.startswith("qwen3") or "thinking" in model
    ):
        return _control("toggle", ["off", "on"], provider_default="on")
    if provider == "hunyuan" and model in {"hy3", "hy3-preview"}:
        return _control("effort", ["low", "medium", "high"], provider_default="low")
    if provider == "hunyuan" and model.startswith(
        ("deepseek-v4-", "deepseek-v3.2")
    ):
        return _control("effort", ["low", "medium", "high"], provider_default="high")
    if provider == "hunyuan" and model.startswith("hunyuan-t1"):
        return _control("effort", ["low", "medium", "high"], provider_default="medium")
    if provider == "hunyuan" and model.startswith(
        ("kimi-k2.7-code", "minimax-m2.7", "minimax-m2.5")
    ):
        return _control(
            "toggle",
            ["on"],
            provider_default="on",
            mandatory=True,
        )
    if provider == "hunyuan" and model.startswith(
        ("glm-5", "kimi-k2.5", "kimi-k2.6", "qwen3.5-", "minimax-m3")
    ):
        return _control("toggle", ["off", "on"], provider_default="on")
    if provider == "claude_code" and model.startswith("claude-"):
        return _control("effort", ["low", "medium", "high", "max"], provider_default="high")
    if provider == "minimax":
        return _control("none", [], provider_default=None)
    return {**_AUTO_ONLY, "source": "unknown", "status": "unknown"}


def failed_reasoning_control(_error: Exception) -> dict[str, Any]:
    return {
        **_AUTO_ONLY,
        "source": "unknown",
        "status": "failed",
        "error": "模型能力获取失败",
    }


def control_from_model(model: Any) -> dict[str, Any]:
    raw = getattr(model, "capability_cache", "") or ""
    try:
        cached = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        cached = {}
    status = str(getattr(model, "capability_status", "") or "unknown")
    if not isinstance(cached, dict) or not cached or status == "failed":
        if status == "failed":
            control = failed_reasoning_control(RuntimeError("capability refresh failed"))
        else:
            control = resolve_reasoning_control(model.provider, model.model)
    else:
        control = dict(cached)
        control.setdefault("status", status)
        control.setdefault("source", "unknown")
        control.setdefault("kind", "none")
        control.setdefault("options", ["auto"])
        control.setdefault("provider_default", None)
        control.setdefault("mandatory", False)
    control["options"] = list(dict.fromkeys(["auto", *control.get("options", [])]))
    updated_at = getattr(model, "capability_updated_at", None)
    control["updated_at"] = updated_at.isoformat() if updated_at is not None else None
    return control


def validate_reasoning(model: Any, reasoning: str) -> dict[str, Any]:
    control = control_from_model(model)
    if reasoning not in control["options"]:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"当前模型不支持推理设置 {reasoning}",
        )
    return control
