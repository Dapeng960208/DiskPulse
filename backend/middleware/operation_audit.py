# -*- coding: utf-8 -*-
"""Fallback result auditing for HTTP operations without lifecycle-specific events."""

from collections.abc import Callable
import re

from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from database import SessionLocal
from services import audit_service


_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_AUTH_LIFECYCLE_PATHS = frozenset({"/users/login", "/users/logout"})
_PROJECT_MEMBERSHIP_PATH = re.compile(r"^/projects/[^/]+/members(?:/[^/]+)?$")
_QUOTA_PATH = re.compile(r"^/(?:groups|storage-usages)/[^/]+/quota$")


def _normalise_api_path(path: str) -> str:
    """Remove the application prefix without retaining any path in audit payloads."""
    normalised = "/" + path.strip("/")
    prefix = "/storage-pulse/api"
    if normalised == prefix:
        return "/"
    if normalised.startswith(f"{prefix}/"):
        return normalised[len(prefix) :]
    return normalised


def _is_auth_lifecycle_path(path: str) -> bool:
    return _normalise_api_path(path) in _AUTH_LIFECYCLE_PATHS


def _has_specialized_lifecycle_audit(path: str) -> bool:
    """Identify routes that already write domain-specific audit events on normal results."""
    normalised = _normalise_api_path(path)
    return bool(
        _PROJECT_MEMBERSHIP_PATH.fullmatch(normalised)
        or _QUOTA_PATH.fullmatch(normalised)
        or normalised == "/ai"
        or normalised.startswith("/ai/")
        or normalised.startswith("/admin/ai")
    )


def _actor_user_id(request) -> int | None:
    current_user = getattr(getattr(request, "state", None), "current_user", None)
    actor_user_id = getattr(current_user, "id", None)
    return actor_user_id if isinstance(actor_user_id, int) else None


class OperationAuditMiddleware(BaseHTTPMiddleware):
    """Append a safe result event after generic management writes and access denials."""

    def __init__(
        self,
        app,
        *,
        session_factory: Callable[[], Session] = SessionLocal,
    ) -> None:
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        try:
            self._record_response_result(request, response)
        except Exception:
            # Audit availability must never alter the completed business response.
            pass
        return response

    def _record_response_result(self, request, response) -> None:
        status_code = response.status_code
        path = request.url.path

        if _is_auth_lifecycle_path(path):
            return

        if status_code in {401, 403}:
            action = "http.request.denied"
            resource_type = "http_endpoint"
            outcome = "denied"
            actor_user_id = _actor_user_id(request)
        else:
            if request.method.upper() not in _WRITE_METHODS:
                return
            if _has_specialized_lifecycle_audit(path):
                return
            actor_user_id = _actor_user_id(request)
            if actor_user_id is None:
                return
            action = f"http.write.{request.method.lower()}"
            resource_type = "management_endpoint"
            outcome = "success" if 200 <= status_code < 400 else "failure"

        db = self._session_factory()
        try:
            audit_service.append_audit_event(
                db,
                context=audit_service.audit_context_for_request(
                    request,
                    actor_user_id=actor_user_id,
                ),
                phase="result",
                action=action,
                resource_type=resource_type,
                outcome=outcome,
                reason_code=f"http_status_{status_code}",
                metadata={"method": request.method.upper(), "status_code": status_code},
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
