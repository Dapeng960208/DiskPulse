# -*- coding: utf-8 -*-
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from crud import auditCrud
from models import AuditEvent
from services.project_access_service import require_project_permission
from utils.auth_service import is_super_admin
from utils.datetime_utils import utc_now


_SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "cookie",
    "prompt",
    "response",
    "request_payload",
    "response_payload",
    "body",
    "message",
    "content",
)
_PATH_KEY_PARTS = ("path", "directory", "filename")
_REDACTED = "[REDACTED]"
_PHASES = {"attempt", "result"}
_OUTCOMES = {"success", "denied", "failure"}
_ai_tool_actor: ContextVar[bool] = ContextVar("ai_tool_actor", default=False)


@contextmanager
def ai_tool_actor_context():
    token = _ai_tool_actor.set(True)
    try:
        yield
    finally:
        _ai_tool_actor.reset(token)


def _normalise_uuid(value: str | UUID) -> str:
    return str(UUID(str(value)))


@dataclass(frozen=True)
class AuditContext:
    request_id: str | UUID
    trace_id: str | UUID
    operation_id: str | UUID
    actor_type: str = "user"
    actor_user_id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _normalise_uuid(self.request_id))
        object.__setattr__(self, "trace_id", _normalise_uuid(self.trace_id))
        object.__setattr__(self, "operation_id", _normalise_uuid(self.operation_id))


def audit_context_for_request(request, *, actor_user_id: int | None, actor_type: str = "user") -> AuditContext:
    """Bind the request correlation values to the user performing a mutation."""
    context = getattr(getattr(request, "state", None), "audit_context", None)
    if not isinstance(context, AuditContext):
        context = AuditContext(
            request_id=uuid4(),
            trace_id=uuid4(),
            operation_id=uuid4(),
        )
    return AuditContext(
        request_id=context.request_id,
        trace_id=context.trace_id,
        operation_id=context.operation_id,
        actor_type="ai_tool" if actor_type == "user" and _ai_tool_actor.get() else actor_type,
        actor_user_id=actor_user_id,
    )


def redact_audit_payload(value: Any, *, key: str | None = None) -> Any:
    """Return a summary-safe deep copy without credentials, prompts, or full paths."""
    key_name = (key or "").casefold()
    if any(part in key_name for part in _SENSITIVE_KEY_PARTS + _PATH_KEY_PARTS):
        return _REDACTED
    if isinstance(value, dict):
        return {str(item_key): redact_audit_payload(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_audit_payload(item, key=key) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        is_windows_path = (
            len(value) >= 3
            and value[0].isalpha()
            and value[1] == ":"
            and value[2] in {"/", "\\"}
        )
        if value.startswith(("/", "\\")) or is_windows_path:
            return _REDACTED
        return value[:512]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:512]


def append_audit_event(
    db: Session,
    *,
    context: AuditContext,
    phase: Literal["attempt", "result"],
    action: str,
    resource_type: str,
    outcome: Literal["success", "denied", "failure"],
    resource_id: int | None = None,
    project_id: int | None = None,
    reason_code: str | None = None,
    before_summary: Any | None = None,
    after_summary: Any | None = None,
    metadata: Any | None = None,
) -> AuditEvent:
    if phase not in _PHASES:
        raise ValueError("unsupported audit phase")
    if outcome not in _OUTCOMES:
        raise ValueError("unsupported audit outcome")
    if not action or not resource_type:
        raise ValueError("audit action and resource type are required")

    event = AuditEvent(
        id=str(uuid4()),
        operation_id=context.operation_id,
        phase=phase,
        occurred_at=utc_now(),
        actor_type=context.actor_type,
        actor_user_id=context.actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        outcome=outcome,
        reason_code=reason_code,
        before_summary=redact_audit_payload(before_summary),
        after_summary=redact_audit_payload(after_summary),
        event_metadata=redact_audit_payload(metadata),
        request_id=context.request_id,
        trace_id=context.trace_id,
    )
    db.add(event)
    db.flush()
    return event


def list_visible_audit_events(
    db: Session,
    *,
    current_user,
    page: int,
    size: int,
    project_id: int | None = None,
    actor_user_id: int | None = None,
    action: str | None = None,
    outcome: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[AuditEvent], int]:
    if not is_super_admin(current_user):
        if project_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="project administrators must select a project",
            )
        require_project_permission(db, current_user, project_id, "project_admin")
    return auditCrud.list_audit_events(
        db,
        page=page,
        size=size,
        project_id=project_id,
        actor_user_id=actor_user_id,
        action=action,
        outcome=outcome,
        start_time=start_time,
        end_time=end_time,
    )


def get_visible_audit_event(db: Session, *, current_user, event_id: str) -> AuditEvent:
    event = auditCrud.get_audit_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="audit event was not found")
    if is_super_admin(current_user):
        return event
    if event.project_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project permission required")
    require_project_permission(db, current_user, event.project_id, "project_admin")
    return event


def serialize_audit_events(db: Session, events: list[AuditEvent], *, current_user) -> list[dict]:
    allowed_project_ids = None
    if not is_super_admin(current_user):
        allowed_project_ids = {event.project_id for event in events if event.project_id is not None}
    associations = auditCrud.get_audit_event_associations(
        db,
        events,
        allowed_project_ids=allowed_project_ids,
    )
    return [serialize_audit_event(event, associations.get(event.id)) for event in events]


def serialize_audit_event(event: AuditEvent, association: dict | None = None) -> dict:
    payload = {
        "id": event.id,
        "operation_id": event.operation_id,
        "phase": event.phase,
        "occurred_at": event.occurred_at,
        "actor_type": event.actor_type,
        "actor_user_id": event.actor_user_id,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": str(event.resource_id) if event.resource_id is not None else None,
        "project_id": event.project_id,
        "outcome": event.outcome,
        "reason_code": event.reason_code,
        "before_summary": redact_audit_payload(event.before_summary),
        "after_summary": redact_audit_payload(event.after_summary),
        "metadata": redact_audit_payload(event.event_metadata),
        "request_id": event.request_id,
        "trace_id": event.trace_id,
    }
    if association is not None:
        payload.update(association)
    return payload
