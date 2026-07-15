# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import AIConfig, AIConversation, AIAuditLog, AIMessage


def list_models(db: Session, *, available_only: bool = False) -> list[AIConfig]:
    statement = select(AIConfig)
    if available_only:
        statement = statement.where(AIConfig.enabled.is_(True), AIConfig.enable_chat.is_(True))
    return list(db.scalars(statement.order_by(AIConfig.name, AIConfig.id)))


def get_model(db: Session, model_id: int) -> AIConfig | None:
    return db.get(AIConfig, model_id)


def add_model(db: Session, model: AIConfig) -> AIConfig:
    db.add(model)
    db.flush()
    return model


def list_conversations(db: Session, user_id: int) -> list[AIConversation]:
    return list(
        db.scalars(
            select(AIConversation)
            .where(AIConversation.user_id == user_id)
            .order_by(AIConversation.updated_at.desc(), AIConversation.id.desc())
        )
    )


def get_conversation(db: Session, conversation_id: int, user_id: int) -> AIConversation | None:
    return db.scalar(
        select(AIConversation).where(
            AIConversation.id == conversation_id,
            AIConversation.user_id == user_id,
        )
    )


def add_conversation(db: Session, conversation: AIConversation) -> AIConversation:
    db.add(conversation)
    db.flush()
    return conversation


def add_message(db: Session, message: AIMessage) -> AIMessage:
    db.add(message)
    db.flush()
    return message


def add_audit(db: Session, audit: AIAuditLog) -> AIAuditLog:
    db.add(audit)
    db.flush()
    return audit


def list_audits(
    db: Session,
    *,
    page: int,
    size: int,
    status_value: str | None = None,
    user_id: int | None = None,
    model_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[AIAuditLog], int]:
    conditions = []
    if status_value:
        conditions.append(AIAuditLog.status == status_value)
    if user_id is not None:
        conditions.append(AIAuditLog.user_id == user_id)
    if model_id is not None:
        conditions.append(AIAuditLog.model_id == model_id)
    if start_time is not None:
        conditions.append(AIAuditLog.started_at >= start_time)
    if end_time is not None:
        conditions.append(AIAuditLog.started_at <= end_time)
    total = int(db.scalar(select(func.count()).select_from(AIAuditLog).where(*conditions)) or 0)
    rows = list(
        db.scalars(
            select(AIAuditLog)
            .where(*conditions)
            .order_by(AIAuditLog.started_at.desc(), AIAuditLog.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return rows, total


def get_audit(db: Session, audit_id: int) -> AIAuditLog | None:
    return db.get(AIAuditLog, audit_id)


def list_conversation_audits(db: Session, conversation_id: int) -> list[AIAuditLog]:
    return list(
        db.scalars(
            select(AIAuditLog)
            .where(AIAuditLog.conversation_id == conversation_id)
            .order_by(AIAuditLog.started_at, AIAuditLog.id)
        )
    )
