# -*- coding: utf-8 -*-
"""Regression contracts for correlation and AI model lifecycle auditing."""

import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from dependencies import get_current_user, get_db, require_super_admin
from middleware.correlation import CorrelationIdMiddleware
from models import AuditEvent, User
from routers import ai_admin
from services import ai_config_service
from services.ai_client import AIClientError


def test_correlation_middleware_returns_ids_when_downstream_raises():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    request_id = "2a48f1f1-78ea-49c1-b3bc-2712720e4c86"
    trace_id = "1e8de2cf-9bdf-4242-a40c-794ce52694ec"
    response = TestClient(app, raise_server_exceptions=False).get(
        "/boom",
        headers={"X-Request-ID": request_id, "X-Trace-ID": trace_id},
    )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == request_id
    assert response.headers["X-Trace-ID"] == trace_id


def _ai_admin_client(session_factory, current_user) -> TestClient:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(ai_admin.router)

    def test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[require_super_admin] = lambda: None
    return TestClient(app)


def test_ai_model_lifecycle_writes_correlated_redacted_unified_audit_events(
    db_session,
    session_factory,
    monkeypatch,
):
    db_session.add(User(id=7, rd_username="audit-admin", username="Audit Admin"))
    db_session.commit()
    client = _ai_admin_client(session_factory, SimpleNamespace(id=7))
    headers = {
        "X-Request-ID": "2a48f1f1-78ea-49c1-b3bc-2712720e4c86",
        "X-Trace-ID": "1e8de2cf-9bdf-4242-a40c-794ce52694ec",
    }
    payload = {
        "name": "audited-model",
        "provider": "openai",
        "api_key": "create-private-api-key",
        "model": "gpt-test",
        "enabled": True,
        "system_prompt": "create-private-system-prompt",
    }

    created = client.post("/admin/ai-models", json=payload, headers=headers)
    assert created.status_code == 201
    model_id = created.json()["id"]

    updated = client.patch(
        f"/admin/ai-models/{model_id}",
        json={
            "api_key": "update-private-api-key",
            "system_prompt": "update-private-system-prompt",
        },
        headers=headers,
    )
    assert updated.status_code == 200

    duplicate = client.post("/admin/ai-models", json=payload, headers=headers)
    assert duplicate.status_code == 409

    monkeypatch.setattr(
        ai_config_service,
        "chat_completion",
        lambda *_args, **_kwargs: SimpleNamespace(text="provider-private-response"),
    )
    tested = client.post(f"/admin/ai-models/{model_id}/test", headers=headers)
    assert tested.status_code == 200

    monkeypatch.setattr(
        ai_config_service,
        "chat_completion",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AIClientError("provider-private-error")
        ),
    )
    failed_test = client.post(f"/admin/ai-models/{model_id}/test", headers=headers)
    assert failed_test.status_code == 502

    deleted = client.delete(f"/admin/ai-models/{model_id}", headers=headers)
    assert deleted.status_code == 204

    events = session_factory().query(AuditEvent).all()
    assert {(event.action, event.outcome) for event in events} == {
        ("ai.model.create", "success"),
        ("ai.model.create", "failure"),
        ("ai.model.update", "success"),
        ("ai.model.delete", "success"),
        ("ai.model.test", "success"),
        ("ai.model.test", "failure"),
    }
    assert all(event.actor_user_id == 7 for event in events)
    assert all(event.request_id == headers["X-Request-ID"] for event in events)
    assert all(event.trace_id == headers["X-Trace-ID"] for event in events)
    persisted = json.dumps(
        [
            {
                "before": event.before_summary,
                "after": event.after_summary,
                "metadata": event.event_metadata,
            }
            for event in events
        ],
        ensure_ascii=False,
    )
    for private_value in (
        "create-private-api-key",
        "update-private-api-key",
        "create-private-system-prompt",
        "update-private-system-prompt",
        "provider-private-response",
        "provider-private-error",
    ):
        assert private_value not in persisted
