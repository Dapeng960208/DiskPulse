# -*- coding: utf-8 -*-
from datetime import datetime
import json

from fastapi import HTTPException, status
from fastapi import FastAPI
import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import aiCrud, incidentAiAgentCrud
from models import AIConfig, AIPlatformSetting
from schemas.aiSchema import AIModelCreate, AIModelDiscoveryRequest, AIModelPatch
from services.ai_client import (
    AIClientError,
    _base_url,
    _headers,
    _timeout,
    chat_completion,
    list_provider_models,
)
from services.ai_reasoning_service import (
    control_from_model,
    failed_reasoning_control,
    resolve_reasoning_control,
)
from services.audit_service import AuditContext, append_audit_event
from services.ai_security import decrypt_secret, encrypt_secret, mask_secret


_UNSET = object()


def _platform_settings(db: Session) -> AIPlatformSetting | None:
    return db.get(AIPlatformSetting, 1)


def _default_model_id(db: Session) -> int | None:
    settings = _platform_settings(db)
    return settings.default_chat_model_id if settings is not None else None


def serialize_model(model: AIConfig, *, is_default: bool = False) -> dict:
    secret = decrypt_secret(model.api_key_encrypted)
    return {
        "id": model.id,
        "name": model.name,
        "description": model.description,
        "provider": model.provider,
        "base_url": model.base_url,
        "api_key_masked": mask_secret(secret),
        "api_key_configured": bool(secret),
        "model": model.model,
        "enabled": model.enabled,
        "enable_chat": model.enable_chat,
        "temperature": float(model.temperature),
        "max_tokens": model.max_tokens,
        "system_prompt": model.system_prompt,
        "capability_status": model.capability_status,
        "capability_error": model.capability_error,
        "capability_updated_at": model.capability_updated_at,
        "reasoning_control": control_from_model(model),
        "is_default": is_default,
        "created_by": model.created_by,
        "updated_by": model.updated_by,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def list_models(db: Session, *, available_only: bool = False) -> list[dict]:
    default_model_id = _default_model_id(db)
    return [
        serialize_model(item, is_default=item.id == default_model_id)
        for item in aiCrud.list_models(db, available_only=available_only)
    ]


def get_platform_settings(db: Session) -> dict:
    settings = _platform_settings(db)
    return {
        "default_chat_model_id": (
            settings.default_chat_model_id if settings is not None else None
        ),
        "name_obfuscation_enabled": (
            bool(settings.name_obfuscation_enabled) if settings is not None else True
        ),
        "updated_by": settings.updated_by if settings is not None else None,
        "created_at": settings.created_at if settings is not None else None,
        "updated_at": settings.updated_at if settings is not None else None,
    }


def get_name_obfuscation_state(db: Session) -> tuple[bool, int]:
    settings = _platform_settings(db)
    if settings is None:
        return True, 1
    return bool(settings.name_obfuscation_enabled), max(1, int(settings.name_obfuscation_epoch or 1))


def update_platform_settings(
    db: Session,
    default_chat_model_id: int | None | object = _UNSET,
    actor_id: int | None = None,
    *,
    name_obfuscation_enabled: bool | object = _UNSET,
) -> dict:
    if actor_id is None:
        raise ValueError("actor_id is required")
    if default_chat_model_id is not _UNSET and default_chat_model_id is not None:
        model = aiCrud.get_model(db, default_chat_model_id)
        if model is None or not model.enabled or not model.enable_chat:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="默认聊天模型必须已启用且允许聊天",
            )
    settings = _platform_settings(db)
    if settings is None:
        settings = AIPlatformSetting(id=1)
        db.add(settings)
    if default_chat_model_id is not _UNSET:
        settings.default_chat_model_id = default_chat_model_id
    if name_obfuscation_enabled is not _UNSET:
        enabled = bool(name_obfuscation_enabled)
        was_enabled = True if settings.name_obfuscation_enabled is None else bool(settings.name_obfuscation_enabled)
        if enabled and not was_enabled:
            settings.name_obfuscation_epoch = max(1, int(settings.name_obfuscation_epoch or 1)) + 1
        settings.name_obfuscation_enabled = enabled
    settings.updated_by = actor_id
    settings.updated_at = datetime.now()
    db.flush()
    db.refresh(settings)
    return get_platform_settings(db)


def get_default_chat_model(db: Session) -> AIConfig | None:
    model_id = _default_model_id(db)
    if model_id is None:
        return None
    model = aiCrud.get_model(db, model_id)
    if model is None or not model.enabled or not model.enable_chat:
        return None
    return model


def _ensure_not_default(db: Session, model_id: int) -> None:
    if _default_model_id(db) == model_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="请先更换默认聊天模型",
        )


def discover_model_capabilities(model: AIConfig) -> dict:
    provider_metadata = None
    if model.provider == "openrouter":
        response = httpx.get(
            f"{_base_url(model)}/models",
            headers=_headers(model),
            timeout=min(_timeout(), 5),
        )
        response.raise_for_status()
        rows = response.json().get("data") or []
        provider_metadata = next(
            (item for item in rows if str(item.get("id")) == model.model),
            None,
        )
    elif model.provider == "claude":
        response = httpx.get(
            f"{_base_url(model)}/v1/models/{model.model}",
            headers=_headers(model),
            timeout=min(_timeout(), 5),
        )
        response.raise_for_status()
        provider_metadata = response.json()
    return resolve_reasoning_control(
        model.provider,
        model.model,
        provider_metadata=provider_metadata,
    )


def refresh_model_capabilities(db: Session, model: AIConfig) -> dict:
    try:
        control = discover_model_capabilities(model)
        model.capability_cache = json.dumps(control, ensure_ascii=False)
        model.capability_status = control["status"]
        model.capability_error = None
    except Exception as error:
        control = failed_reasoning_control(error)
        model.capability_cache = json.dumps(control, ensure_ascii=False)
        model.capability_status = "failed"
        model.capability_error = "模型能力获取失败"
    model.capability_updated_at = datetime.now()
    db.flush()
    db.refresh(model)
    return serialize_model(model, is_default=_default_model_id(db) == model.id)


def refresh_model_capabilities_by_id(db: Session, model_id: int) -> dict:
    return refresh_model_capabilities(db, _get_or_404(db, model_id))


def _prime_official_capability(model: AIConfig) -> None:
    control = resolve_reasoning_control(model.provider, model.model)
    model.capability_cache = json.dumps(control, ensure_ascii=False)
    model.capability_status = control["status"]
    model.capability_error = None
    model.capability_updated_at = datetime.now()


def _refresh_dynamic_capability(db: Session, model: AIConfig) -> dict:
    if model.provider in {"openrouter", "claude"}:
        return refresh_model_capabilities(db, model)
    return serialize_model(model, is_default=_default_model_id(db) == model.id)


def _get_or_404(db: Session, model_id: int) -> AIConfig:
    model = aiCrud.get_model(db, model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在")
    return model


def _discovery_config(
    *,
    provider: str,
    base_url: str,
    api_key_encrypted: str,
) -> AIConfig:
    return AIConfig(
        name="model-discovery",
        provider=provider,
        base_url=base_url,
        api_key_encrypted=api_key_encrypted,
        model="",
    )


def _resolve_model_identifier(model: AIConfig) -> str:
    configured = (model.model or "").strip()
    return configured or list_provider_models(model)[0]


def discover_models(payload: AIModelDiscoveryRequest) -> dict:
    config = _discovery_config(
        provider=payload.provider,
        base_url=payload.base_url,
        api_key_encrypted=encrypt_secret(payload.api_key),
    )
    models = list_provider_models(config)
    return {"models": models, "default_model": models[0]}


def _append_model_audit(
    db: Session,
    *,
    audit_context: AuditContext | None,
    action: str,
    outcome: str,
    model_id: int | None = None,
    reason_code: str | None = None,
) -> None:
    if audit_context is None:
        return
    append_audit_event(
        db,
        context=audit_context,
        phase="result",
        action=action,
        resource_type="ai_model",
        resource_id=model_id,
        outcome=outcome,
        reason_code=reason_code,
    )


def _record_model_failure(
    db: Session,
    *,
    audit_context: AuditContext | None,
    action: str,
    model_id: int | None,
    reason_code: str,
) -> None:
    db.rollback()
    if audit_context is None:
        return
    try:
        _append_model_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="failure",
            model_id=model_id,
            reason_code=reason_code,
        )
        db.commit()
    except Exception:
        db.rollback()


def create_model(
    db: Session,
    payload: AIModelCreate,
    actor_id: int,
    *,
    audit_context: AuditContext | None = None,
) -> dict:
    action = "ai.model.create"
    try:
        values = payload.model_dump(exclude={"api_key"})
        api_key_encrypted = encrypt_secret(payload.api_key)
        values["model"] = values["model"].strip()
        if not values["model"]:
            values["model"] = _resolve_model_identifier(
                _discovery_config(
                    provider=values["provider"],
                    base_url=values["base_url"],
                    api_key_encrypted=api_key_encrypted,
                )
            )
        model = AIConfig(
            **values,
            api_key_encrypted=api_key_encrypted,
            created_by=actor_id,
            updated_by=actor_id,
        )
        _prime_official_capability(model)
        aiCrud.add_model(db, model)
        _append_model_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            model_id=model.id,
        )
        db.flush()
        db.refresh(model)
    except IntegrityError as error:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=None,
            reason_code="ai_model_conflict",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI 模型名称已存在") from error
    except Exception:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=None,
            reason_code="ai_model_create_failed",
        )
        raise
    return _refresh_dynamic_capability(db, model)


def update_model(
    db: Session,
    model_id: int,
    payload: AIModelPatch,
    actor_id: int,
    *,
    audit_context: AuditContext | None = None,
) -> dict:
    action = "ai.model.update"
    try:
        model = _get_or_404(db, model_id)
        values = payload.model_dump(exclude_unset=True, exclude={"api_key"})
        requested_model = values.pop("model", None)
        disabling_default = (
            ("enabled" in values and not values["enabled"])
            or ("enable_chat" in values and not values["enable_chat"])
        )
        if disabling_default:
            _ensure_not_default(db, model_id)
        for key, value in values.items():
            setattr(model, key, value)
        if "api_key" in payload.model_fields_set:
            model.api_key_encrypted = encrypt_secret(payload.api_key or "")
        if requested_model is not None:
            model.model = requested_model
            model.model = _resolve_model_identifier(model)
        model.updated_by = actor_id
        model.updated_at = datetime.now()
        if {"provider", "base_url", "model", "api_key"} & payload.model_fields_set:
            _prime_official_capability(model)
        _append_model_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            model_id=model.id,
        )
        db.flush()
        db.refresh(model)
    except IntegrityError as error:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_conflict",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI 模型名称已存在") from error
    except HTTPException:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_not_found",
        )
        raise
    except Exception:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_update_failed",
        )
        raise
    if {"provider", "base_url", "model", "api_key"} & payload.model_fields_set:
        return _refresh_dynamic_capability(db, model)
    return serialize_model(model, is_default=_default_model_id(db) == model.id)


def delete_model(
    db: Session,
    model_id: int,
    *,
    audit_context: AuditContext | None = None,
) -> None:
    action = "ai.model.delete"
    try:
        model = _get_or_404(db, model_id)
        if incidentAiAgentCrud.model_is_bound_to_settings(db, model_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="模型正被事件 AI 处置设置引用，请先移除候选模型")
        _ensure_not_default(db, model_id)
        db.delete(model)
        _append_model_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            model_id=model_id,
        )
        db.flush()
    except IntegrityError as error:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_conflict",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="模型已被会话使用，请先停用") from error
    except HTTPException as error:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="incident_ai_model_bound" if error.status_code == status.HTTP_409_CONFLICT else "ai_model_not_found",
        )
        raise
    except Exception:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_delete_failed",
        )
        raise


def test_model(
    db: Session,
    model_id: int,
    *,
    audit_context: AuditContext | None = None,
) -> dict:
    action = "ai.model.test"
    try:
        model = _get_or_404(db, model_id)
        messages = [{"role": "user", "content": "请回复 OK"}]
        if model.provider == "claude_code":
            from services.claude_code_adapter import claude_code_completion_stream

            events = list(
                claude_code_completion_stream(
                    model,
                    messages,
                    app=FastAPI(),
                    registry={},
                    current_user=None,
                    user_id=None,
                    timeout_seconds=_timeout(),
                )
            )
            result_text = events[-1].text
        else:
            result_text = chat_completion(model, messages).text
    except AIClientError as error:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_test_failed",
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except HTTPException:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_not_found",
        )
        raise
    except Exception:
        _record_model_failure(
            db,
            audit_context=audit_context,
            action=action,
            model_id=model_id,
            reason_code="ai_model_test_failed",
        )
        raise
    _append_model_audit(
        db,
        audit_context=audit_context,
        action=action,
        outcome="success",
        model_id=model.id,
    )
    db.flush()
    _refresh_dynamic_capability(db, model)
    return {"ok": True, "message": "连接成功", "reply": result_text[:500]}
