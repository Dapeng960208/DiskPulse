# -*- coding: utf-8 -*-
"""Contract tests for the fallback HTTP operation-audit middleware."""

import importlib
import json
from types import SimpleNamespace
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.testclient import TestClient
import pytest

from middleware.correlation import CorrelationIdMiddleware
from models import AuditEvent, User


def _operation_audit_middleware():
    module = importlib.import_module("middleware.operation_audit")
    return module.OperationAuditMiddleware


def _client_with_operation_audit(session_factory, *, actor_id: int = 7) -> TestClient:
    app = FastAPI()
    app.add_middleware(_operation_audit_middleware(), session_factory=session_factory)
    app.add_middleware(CorrelationIdMiddleware)

    @app.middleware("http")
    async def db_session_middleware(request: Request, call_next):
        request.state.db = session_factory()
        try:
            return await call_next(request)
        finally:
            request.state.db.close()

    def authenticate(request: Request):
        request.state.current_user = SimpleNamespace(id=actor_id)

    @app.api_route(
        "/admin/users/{resource_id}",
        methods=["POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(authenticate)],
    )
    def write_management_resource(resource_id: int):
        return Response(status_code=201)

    @app.get("/denied/{status_code}")
    def denied_request(status_code: int):
        raise HTTPException(status_code=status_code, detail="not permitted")

    @app.api_route(
        "/{resource_path:path}",
        methods=["POST", "PUT", "PATCH", "DELETE"],
        dependencies=[Depends(authenticate)],
    )
    def other_management_write(resource_path: str):
        return Response(status_code=201)

    return TestClient(app)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_authenticated_management_writes_append_safe_result_events(session_factory, db_session, method):
    db_session.add(User(id=7, rd_username="audit-admin"))
    db_session.commit()
    client = _client_with_operation_audit(session_factory)
    request_id = "2a48f1f1-78ea-49c1-b3bc-2712720e4c86"
    trace_id = "1e8de2cf-9bdf-4242-a40c-794ce52694ec"

    response = client.request(
        method,
        "/admin/users/42?token=private-token",
        headers={"X-Request-ID": request_id, "X-Trace-ID": trace_id},
        json={"password": "private-password", "linux_path": "/private/alice"},
    )

    assert response.status_code == 201
    event = session_factory().query(AuditEvent).one()
    assert (event.action, event.resource_type, event.outcome) == (
        f"http.write.{method.lower()}",
        "management_endpoint",
        "success",
    )
    assert event.reason_code == "http_status_201"
    assert event.actor_user_id == 7
    assert event.event_metadata == {"method": method, "status_code": 201}
    assert event.request_id == request_id
    assert event.trace_id == trace_id
    assert str(UUID(event.operation_id)) == event.operation_id
    persisted = json.dumps(
        {
            "metadata": event.event_metadata,
            "before": event.before_summary,
            "after": event.after_summary,
        },
        ensure_ascii=False,
    )
    assert "private-token" not in persisted
    assert "private-password" not in persisted
    assert "/private/alice" not in persisted


@pytest.mark.parametrize("status_code", [401, 403])
def test_http_authentication_and_authorization_denials_append_safe_result_events(
    session_factory,
    status_code,
):
    client = _client_with_operation_audit(session_factory)

    response = client.get(f"/denied/{status_code}?authorization=private-token")

    assert response.status_code == status_code
    event = session_factory().query(AuditEvent).one()
    assert (event.action, event.resource_type, event.outcome) == (
        "http.request.denied",
        "http_endpoint",
        "denied",
    )
    assert event.reason_code == f"http_status_{status_code}"
    assert event.actor_user_id is None
    assert event.event_metadata == {"method": "GET", "status_code": status_code}
    assert "private-token" not in json.dumps(event.event_metadata, ensure_ascii=False)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/users/login"),
        ("POST", "/users/logout"),
        ("POST", "/projects/11/members"),
        ("PATCH", "/groups/11/quota"),
        ("PATCH", "/storage-usages/11/quota"),
        ("POST", "/ai/conversations"),
        ("PATCH", "/admin/ai-models/11"),
    ],
)
def test_routes_with_specialized_lifecycle_audits_are_not_duplicated(
    session_factory,
    db_session,
    method,
    path,
):
    db_session.add(User(id=7, rd_username="audit-admin"))
    db_session.commit()
    client = _client_with_operation_audit(session_factory)

    response = client.request(method, path)

    assert response.status_code == 201
    assert session_factory().query(AuditEvent).count() == 0


def test_audit_write_failure_never_changes_the_business_response():
    class FailingAuditSession:
        instances = []

        def __init__(self):
            self.rolled_back = False
            self.closed = False
            type(self).instances.append(self)

        def add(self, _event):
            raise RuntimeError("audit database unavailable")

        def flush(self):  # pragma: no cover - add() fails first
            raise AssertionError("flush must not run")

        def commit(self):
            raise AssertionError("commit must not run")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    client = _client_with_operation_audit(FailingAuditSession)

    response = client.post("/admin/users/42")

    assert response.status_code == 201
    assert any(instance.rolled_back for instance in FailingAuditSession.instances)
    assert all(instance.closed for instance in FailingAuditSession.instances)
