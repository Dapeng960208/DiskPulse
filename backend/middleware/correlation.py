# -*- coding: utf-8 -*-
from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from services.audit_service import AuditContext


REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"


def _validated_uuid(value: str | None) -> str:
    if not value:
        return str(uuid4())
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        return str(uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach trusted request correlation identifiers before route dependencies run."""

    async def dispatch(self, request, call_next):
        context = AuditContext(
            request_id=_validated_uuid(request.headers.get(REQUEST_ID_HEADER)),
            trace_id=_validated_uuid(request.headers.get(TRACE_ID_HEADER)),
            operation_id=str(uuid4()),
        )
        request.state.audit_context = context
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = context.request_id
        response.headers[TRACE_ID_HEADER] = context.trace_id
        return response
