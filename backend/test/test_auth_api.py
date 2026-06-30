# -*- coding: utf-8 -*-
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import Base
import models  # noqa: F401
from routers import projects, users


class AuthApiTest(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}, clear=False)
        self.env_patcher.start()
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        app = FastAPI()
        storage_router = APIRouter(prefix="/storage-pulse/api")
        storage_router.include_router(users.router)
        storage_router.include_router(projects.router)
        app.include_router(storage_router)

        @app.middleware("http")
        async def db_session_middleware(request: Request, call_next):
            request.state.db = self.SessionLocal()
            try:
                return await call_next(request)
            finally:
                request.state.db.close()

        self.client = TestClient(app)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.env_patcher.stop()

    def test_login_issues_frontend_compatible_token_and_upserts_user(self):
        profile = {
            "username": "alice",
            "display_name": "Alice Zhang",
            "email": "alice@example.com",
            "user_dn": "CN=Alice,OU=Users,DC=example,DC=com",
            "matched_base": "OU=Users,DC=example,DC=com",
        }
        with patch.dict(os.environ, {"SUPER_ADMIN_USERNAMES": "alice"}, clear=False):
            with patch("utils.auth_service.ldap_authenticate", return_value=profile):
                response = self.client.post(
                    "/storage-pulse/api/users/login",
                    json={"username": "alice", "password": "secret-password"},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("token", payload["result"])
            self.assertEqual(payload["result"]["token_type"], "bearer")

            token = payload["result"]["token"]
            profile_response = self.client.get(
                "/storage-pulse/api/users/current/profile",
                headers={"Authorization": token},
            )
            self.assertEqual(profile_response.status_code, 200)
            account = profile_response.json()["result"]
            self.assertEqual(account["commonName"], "Alice Zhang")
            self.assertEqual(account["roleCodes"], ["superadmin"])
            self.assertEqual(account["permissionCodes"], [["*", "*", "*"]])
            self.assertEqual(account["extensionAttributes"]["rdUsername"], "alice")

    def test_login_rejects_invalid_credentials_without_echoing_password(self):
        with patch("utils.auth_service.ldap_authenticate", return_value=None):
            response = self.client.post(
                "/storage-pulse/api/users/login",
                json={"username": "alice", "password": "secret-password"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("secret-password", response.text)

    def test_profile_and_business_api_require_token(self):
        profile_response = self.client.get("/storage-pulse/api/users/current/profile")
        users_response = self.client.get("/storage-pulse/api/users/")

        self.assertEqual(profile_response.status_code, 401)
        self.assertEqual(users_response.status_code, 401)

    def test_business_api_accepts_bearer_token_and_logout_returns_null_result(self):
        profile = {
            "username": "bob",
            "display_name": "Bob Li",
            "email": "bob@example.com",
            "user_dn": "CN=Bob,OU=Users,DC=example,DC=com",
            "matched_base": "OU=Users,DC=example,DC=com",
        }
        with patch("utils.auth_service.ldap_authenticate", return_value=profile):
            login_response = self.client.post(
                "/storage-pulse/api/users/login",
                json={"username": "bob", "password": "secret-password"},
            )

        token = login_response.json()["result"]["token"]
        users_response = self.client.get(
            "/storage-pulse/api/users/",
            headers={"Authorization": f"Bearer {token}"},
        )
        logout_response = self.client.post(
            "/storage-pulse/api/users/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(users_response.status_code, 200)
        self.assertEqual(logout_response.status_code, 200)
        self.assertIsNone(logout_response.json()["result"])


if __name__ == "__main__":
    unittest.main()
