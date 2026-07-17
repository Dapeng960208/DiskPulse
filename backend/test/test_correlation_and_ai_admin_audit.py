# -*- coding: utf-8 -*-
"""Regression contracts for correlation and AI model lifecycle auditing."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.correlation import CorrelationIdMiddleware


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
