# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from appConfig import base_config
from main import create_app
from routers.transactional import TransactionalAPIRouter, skip_write_transaction


class RecordingSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def _client_for(router: TransactionalAPIRouter, session: RecordingSession) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    @app.middleware("http")
    async def bind_session(request: Request, call_next):
        request.state.db = session
        return await call_next(request)

    return TestClient(app, raise_server_exceptions=False)


def test_router_write_success_commits_once() -> None:
    router = TransactionalAPIRouter(prefix="/transactions")

    @router.post("/success")
    def succeed():
        return {"ok": True}

    session = RecordingSession()
    response = _client_for(router, session).post("/transactions/success")

    assert response.status_code == 200
    assert session.commits == 1
    assert session.rollbacks == 0


def test_router_write_exception_rolls_back_and_preserves_http_error() -> None:
    router = TransactionalAPIRouter(prefix="/transactions")

    @router.post("/failure")
    def fail():
        raise HTTPException(status_code=418, detail="teapot")

    session = RecordingSession()
    response = _client_for(router, session).post("/transactions/failure")

    assert response.status_code == 418
    assert response.json() == {"detail": "teapot"}
    assert session.commits == 0
    assert session.rollbacks == 1


def test_router_read_does_not_open_a_write_transaction() -> None:
    router = TransactionalAPIRouter(prefix="/transactions")

    @router.get("/read")
    def read():
        return {"ok": True}

    session = RecordingSession()
    response = _client_for(router, session).get("/transactions/read")

    assert response.status_code == 200
    assert session.commits == 0
    assert session.rollbacks == 0


def test_router_can_exclude_streaming_write_from_request_transaction() -> None:
    router = TransactionalAPIRouter(prefix="/transactions")

    @router.post("/stream")
    @skip_write_transaction
    def stream():
        return {"ok": True}

    session = RecordingSession()
    response = _client_for(router, session).post("/transactions/stream")

    assert response.status_code == 200
    assert session.commits == 0
    assert session.rollbacks == 0


def test_create_app_rejects_jwt_secret_shorter_than_32_characters() -> None:
    original_secret = base_config.get("jwt.secret_key")
    try:
        base_config.set("jwt.secret_key", "x" * 31)

        try:
            create_app()
        except RuntimeError as error:
            assert str(error) == "jwt.secret_key must be at least 32 characters"
        else:
            raise AssertionError("create_app accepted a 31-character JWT secret")
    finally:
        base_config.set("jwt.secret_key", original_secret)


def test_create_app_rejects_wildcard_cors_origin_with_credentials() -> None:
    original_origins = base_config.get("application.cors_origins")
    try:
        base_config.set("application.cors_origins", ["*"])

        try:
            create_app()
        except RuntimeError as error:
            assert str(error) == "application.cors_origins must not contain '*' when credentials are enabled"
        else:
            raise AssertionError("create_app accepted wildcard CORS with credentials")
    finally:
        base_config.set("application.cors_origins", original_origins)
