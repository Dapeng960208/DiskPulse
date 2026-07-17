# -*- coding: utf-8 -*-
"""RED contract for request correlation and append-only unified audit events."""

import importlib
import json
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def _uuid(value: str) -> str:
    return str(UUID(value))


def _correlation_client() -> TestClient:
    correlation = importlib.import_module("middleware.correlation")
    app = FastAPI()
    app.add_middleware(correlation.CorrelationIdMiddleware)

    @app.get("/correlation")
    def correlation_view(request: Request):
        context = request.state.audit_context
        return {
            "request_id": str(context.request_id),
            "trace_id": str(context.trace_id),
            "operation_id": str(context.operation_id),
        }

    return TestClient(app)


def test_correlation_middleware_preserves_valid_request_and_trace_ids():
    client = _correlation_client()
    request_id = "2a48f1f1-78ea-49c1-b3bc-2712720e4c86"
    trace_id = "1e8de2cf-9bdf-4242-a40c-794ce52694ec"

    response = client.get(
        "/correlation",
        headers={"X-Request-ID": request_id, "X-Trace-ID": trace_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert response.headers["X-Trace-ID"] == trace_id
    assert response.json()["request_id"] == request_id
    assert response.json()["trace_id"] == trace_id
    assert _uuid(response.json()["operation_id"])


def test_correlation_middleware_replaces_invalid_ids_with_safe_uuids():
    client = _correlation_client()

    response = client.get(
        "/correlation",
        headers={"X-Request-ID": "not-a-uuid", "X-Trace-ID": "../../secret"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "not-a-uuid"
    assert response.headers["X-Trace-ID"] != "../../secret"
    assert _uuid(response.headers["X-Request-ID"])
    assert _uuid(response.headers["X-Trace-ID"])
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.json()["trace_id"] == response.headers["X-Trace-ID"]


def test_audit_redaction_removes_secrets_paths_and_raw_prompt_content():
    audit_service = importlib.import_module("services.audit_service")
    payload = {
        "Authorization": "Bearer private-token",
        "nested": {"apiKey": "provider-secret"},
        "linux_path": "/mnt/diskpulse/private/alice",
        "prompt": "请总结 alice 的私有目录配额",
        "response_payload": {"content": "模型原始回复"},
        "hard_limit": 1024,
    }

    redacted = audit_service.redact_audit_payload(payload)
    serialized = json.dumps(redacted, ensure_ascii=False)

    for forbidden in (
        "private-token",
        "provider-secret",
        "/mnt/diskpulse/private/alice",
        "请总结 alice 的私有目录配额",
        "模型原始回复",
    ):
        assert forbidden not in serialized
    assert redacted["hard_limit"] == 1024
    assert payload["Authorization"] == "Bearer private-token"


def test_append_audit_event_creates_a_new_redacted_event_without_committing():
    audit_service = importlib.import_module("services.audit_service")

    class RecordingSession:
        def __init__(self):
            self.added = []
            self.flushed = False

        def add(self, event):
            self.added.append(event)

        def flush(self):
            self.flushed = True

        def commit(self):  # pragma: no cover - assertion guard for transaction ownership
            raise AssertionError("append_audit_event must not commit the caller transaction")

    context = audit_service.AuditContext(
        request_id="0a79076d-4bc8-4d20-b78c-60e214617515",
        trace_id="ca277c09-4d55-4328-859c-975b8bdac736",
        operation_id="6b16544a-75a5-42df-9728-0c2e214f3097",
        actor_user_id=7,
    )
    db = RecordingSession()

    event = audit_service.append_audit_event(
        db,
        context=context,
        phase="result",
        action="quota.adjust",
        resource_type="storage_usage",
        resource_id=42,
        project_id=9,
        outcome="success",
        before_summary={"linux_path": "/mnt/diskpulse/private/alice", "hard_limit": 100},
        after_summary={"linux_path": "/mnt/diskpulse/private/alice", "hard_limit": 120},
        metadata={"token": "do-not-store"},
    )

    assert db.added == [event]
    assert db.flushed is True
    assert str(event.request_id) == str(context.request_id)
    assert str(event.trace_id) == str(context.trace_id)
    assert str(event.operation_id) == str(context.operation_id)
    assert event.actor_user_id == 7
    assert event.action == "quota.adjust"
    assert event.resource_type == "storage_usage"
    assert event.resource_id == 42
    assert event.project_id == 9
    assert event.phase == "result"
    assert event.outcome == "success"
    persisted = json.dumps(
        {"before": event.before_summary, "after": event.after_summary, "metadata": event.metadata},
        ensure_ascii=False,
    )
    assert "/mnt/diskpulse/private/alice" not in persisted
    assert "do-not-store" not in persisted
