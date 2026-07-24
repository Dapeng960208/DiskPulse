# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from appConfig import base_config

TEST_CONFIG_PATH = BACKEND_ROOT / "config.test.yml"
base_config.load(TEST_CONFIG_PATH)

from database import Base
from dependencies import require_authenticated_request
from utils import security
from utils.security import issue_token


class FakeTokenRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def set(self, key, value, ex=None):
        self.values[key] = value
        self.expirations[key] = ex
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.expirations.pop(key, None)
        return int(self.values.pop(key, None) is not None)


class FakeQuotaRedis(FakeTokenRedis):
    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        return super().set(key, value, ex=ex)

    def setex(self, key, ttl, value):
        return self.set(key, value, ex=ttl)

    def eval(self, _script, _numkeys, key, value):
        if self.get(key) != value:
            return 0
        return self.delete(key)


@pytest.fixture(autouse=True)
def token_redis(monkeypatch):
    client = FakeTokenRedis()
    monkeypatch.setattr(security, "_redis_client", lambda: client, raising=False)
    return client


@pytest.fixture(autouse=True)
def quota_redis(monkeypatch):
    client = FakeQuotaRedis()
    monkeypatch.setattr("services.quotaService._quota_redis_client", lambda: client, raising=False)
    return client


@pytest.fixture(autouse=True)
def reset_runtime_config():
    base_config.load(TEST_CONFIG_PATH)
    yield


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client_factory(session_factory):
    def build_client(routers, *, authenticated=True, headers=None, route_setup=None):
        app = FastAPI()
        dependencies = [Depends(require_authenticated_request)] if authenticated else []
        storage_router = APIRouter(prefix="/storage-pulse/api", dependencies=dependencies)

        for router in routers:
            storage_router.include_router(router)
        if route_setup is not None:
            route_setup(storage_router)

        app.include_router(storage_router)

        @app.middleware("http")
        async def db_session_middleware(request: Request, call_next):
            request.state.db = session_factory()
            try:
                return await call_next(request)
            finally:
                request.state.db.close()

        return TestClient(app, headers=headers or {})

    return build_client


@pytest.fixture
def auth_headers():
    base_config.set("jwt.secret_key", "test-jwt-secret-key-for-unit-tests-32")
    return {"Authorization": f"Bearer {issue_token(1)}"}
