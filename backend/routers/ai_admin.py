# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db, require_super_admin
from schemas.aiSchema import AIModelCreate, AIModelPatch
from services import ai_audit_service, ai_config_service


router = APIRouter(
    prefix="/admin",
    tags=["ai-admin"],
    dependencies=[Depends(require_super_admin)],
)


@router.get(
    "/ai-models",
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "list_ai_models",
        "ai_description": "查询 AI 模型配置",
    },
)
def models(_current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_config_service.list_models(db)


@router.post(
    "/ai-models",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "create_ai_model",
        "ai_description": "创建 AI 模型配置",
    },
)
def create_model(payload: AIModelCreate, current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_config_service.create_model(db, payload, current_user.id)


@router.patch(
    "/ai-models/{model_id}",
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "update_ai_model",
        "ai_description": "更新 AI 模型配置",
    },
)
def update_model(
    model_id: int,
    payload: AIModelPatch,
    current_user: CurrentUserDep,
    db: Session = Depends(get_db),
):
    return ai_config_service.update_model(db, model_id, payload, current_user.id)


@router.delete(
    "/ai-models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "delete_ai_model",
        "ai_description": "删除 AI 模型配置",
    },
)
def delete_model(model_id: int, _current_user: CurrentUserDep, db: Session = Depends(get_db)):
    ai_config_service.delete_model(db, model_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ai-models/{model_id}/test")
def test_model(model_id: int, _current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_config_service.test_model(db, model_id)


@router.get("/ai-audits")
def audits(
    _current_user: CurrentUserDep,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_value: str | None = Query(default=None, alias="status"),
    user_id: int | None = None,
    model_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: Session = Depends(get_db),
):
    return ai_audit_service.list_audits(
        db,
        page=page,
        size=size,
        status_value=status_value,
        user_id=user_id,
        model_id=model_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/ai-audits/conversations/{conversation_id}")
def conversation_audits(conversation_id: int, _current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_audit_service.get_conversation_audits(db, conversation_id)


@router.get("/ai-audits/{audit_id}")
def audit(audit_id: int, _current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_audit_service.get_audit(db, audit_id)
