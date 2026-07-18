# -*- coding: utf-8 -*-
import logging
from uuid import UUID, uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from services.audit_service import AuditContext


logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"


def _validated_uuid(value: str | None) -> str:
    if not value:
        return str(uuid4())
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        return str(uuid4())


class CorrelationIdMiddleware:
    """Attach trusted request correlation identifiers before route dependencies run."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        context = AuditContext(
            request_id=_validated_uuid(MutableHeaders(scope=scope).get(REQUEST_ID_HEADER)),
            trace_id=_validated_uuid(MutableHeaders(scope=scope).get(TRACE_ID_HEADER)),
            operation_id=str(uuid4()),
        )
        scope.setdefault("state", {})["audit_context"] = context
        response_started = False

        async def send_with_correlation(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = context.request_id
                headers[TRACE_ID_HEADER] = context.trace_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        except Exception as error:
            if not response_started:
                # Review source: this fallback consumed the exception without a
                # server record. Resolution: log only trusted correlation IDs
                # plus exception context, while the client still gets generic 500.
                logger.exception(
                    "Unhandled HTTP request error request_id=%s trace_id=%s",
                    context.request_id,
                    context.trace_id,
                )
                await PlainTextResponse("Internal Server Error", status_code=500)(
                    scope,
                    receive,
                    send_with_correlation,
                )
                # Return after sending fallback response to avoid double-response attempt
                return
            # Re-raise if response already started so the server logs the error
            raise
