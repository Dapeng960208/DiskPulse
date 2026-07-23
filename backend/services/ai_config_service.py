# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import aiCrud, incidentAiAgentCrud
from models import AIConfig
from schemas.aiSchema import AIModelCreate, AIModelPatch
from services.ai_client import AIClientError, chat_completion
from services.audit_service import AuditContext, append_audit_event
from services.ai_security import decrypt_secret, encrypt_secret, mask_secret


def serialize_model(model: AIConfig) -> dict:
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
        "created_by": model.created_by,
        "updated_by": model.updated_by,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def list_models(db: Session, *, available_only: bool = False) -> list[dict]:
    return [serialize_model(item) for item in aiCrud.list_models(db, available_only=available_only)]


def _get_or_404(db: Session, model_id: int) -> AIConfig:
    model = aiCrud.get_model(db, model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在")
    return model


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
        model = AIConfig(
            **values,
            api_key_encrypted=encrypt_secret(payload.api_key),
            created_by=actor_id,
            updated_by=actor_id,
        )
        aiCrud.add_model(db, model)
        _append_model_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            model_id=model.id,
        )
        db.commit()
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
    return serialize_model(model)


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
        for key, value in values.items():
            setattr(model, key, value)
        if "api_key" in payload.model_fields_set:
            model.api_key_encrypted = encrypt_secret(payload.api_key or "")
        model.updated_by = actor_id
        model.updated_at = datetime.now()
        _append_model_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            model_id=model.id,
        )
        db.commit()
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
    return serialize_model(model)


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
        db.delete(model)
        _append_model_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            model_id=model_id,
        )
        db.commit()
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
        result = chat_completion(model, [{"role": "user", "content": "请回复 OK"}])
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
    db.commit()
    return {"ok": True, "message": "连接成功", "reply": result.text[:500]}
