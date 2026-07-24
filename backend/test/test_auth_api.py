# -*- coding: utf-8 -*-
import json
from unittest.mock import patch

import redis
import pytest
from fastapi import HTTPException

from appConfig import base_config
import models  # noqa: F401
from routers import projects, users
from utils import security
from utils.security import decode_token, issue_token


def _profile(username="alice", display_name="Alice Zhang", email="alice@example.com"):
    return {
        "username": username,
        "display_name": display_name,
        "email": email,
        "user_dn": f"CN={display_name},OU=Users,DC=example,DC=com",
        "matched_base": "OU=Users,DC=example,DC=com",
    }


def test_login_issues_frontend_compatible_token_and_upserts_user(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["alice"])
    client = api_client_factory([users.router, projects.router], authenticated=False)

    with patch("utils.auth_service.ldap_authenticate", return_value=_profile()):
        response = client.post(
            "/storage-pulse/api/users/login",
            json={"username": "alice", "password": "secret-password"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "token" in payload["result"]
    assert payload["result"]["token_type"] == "bearer"

    token = payload["result"]["token"]
    profile_response = client.get(
        "/storage-pulse/api/users/current/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200
    account = profile_response.json()["result"]
    assert account["commonName"] == "Alice Zhang"
    assert account["roleCodes"] == ["superadmin"]
    assert account["permissionCodes"] == [["*", "*", "*"]]
    assert account["extensionAttributes"]["rdUsername"] == "alice"
    assert account["time_zone"] is None


def test_current_user_can_save_a_valid_iana_timezone_but_cannot_submit_invalid_values(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router], authenticated=False)

    with patch("utils.auth_service.ldap_authenticate", return_value=_profile()):
        token = client.post(
            "/storage-pulse/api/users/login",
            json={"username": "alice", "password": "secret-password"},
        ).json()["result"]["token"]

    headers = {"Authorization": f"Bearer {token}"}
    saved = client.patch(
        "/storage-pulse/api/users/current/profile",
        json={"time_zone": "America/Los_Angeles"},
        headers=headers,
    )
    invalid = client.patch(
        "/storage-pulse/api/users/current/profile",
        json={"time_zone": "not/a-time-zone"},
        headers=headers,
    )
    profile = client.get("/storage-pulse/api/users/current/profile", headers=headers)

    assert saved.status_code == 200
    assert saved.json()["result"]["time_zone"] == "America/Los_Angeles"
    assert invalid.status_code == 422
    assert profile.json()["result"]["time_zone"] == "America/Los_Angeles"


def test_authenticated_user_can_list_supported_iana_timezones(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router], authenticated=False)
    current_user = models.User(id=7, rd_username="alice", username="Alice Zhang")
    token = issue_token(current_user.id)

    with patch("dependencies.usersCrud.get_user_by_id", return_value=current_user):
        response = client.get(
            "/storage-pulse/api/users/current/time-zones",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert "Asia/Shanghai" in response.json()["result"]
    assert "America/Los_Angeles" in response.json()["result"]


def test_access_token_defaults_to_seven_days(token_redis):
    base_config.config["jwt"].pop("access_ttl_minutes")

    payload = decode_token(issue_token(7))

    assert payload["exp"] - payload["iat"] == 7 * 24 * 60 * 60


def test_access_token_is_hashed_in_redis_with_matching_ttl(token_redis):
    base_config.set("jwt.access_ttl_minutes", 7 * 24 * 60)

    token = issue_token(7)

    assert (
        len(token_redis.values),
        list(token_redis.expirations.values()),
        token in token_redis.values.values(),
    ) == (1, [7 * 24 * 60 * 60], False)


def test_valid_signed_token_must_exist_in_redis(token_redis):
    token = issue_token(7)
    token_redis.values.clear()

    with pytest.raises(HTTPException) as error:
        decode_token(token)

    assert error.value.status_code == 401


def test_authentication_fails_closed_when_redis_is_unavailable(token_redis, monkeypatch):
    token = issue_token(7)

    class FailedRedis:
        def get(self, _key):
            raise redis.RedisError("offline")

    monkeypatch.setattr(security, "_redis_client", lambda: FailedRedis())

    with pytest.raises(HTTPException) as error:
        decode_token(token)

    assert error.value.status_code == 503


def test_login_rejects_invalid_credentials_without_echoing_password(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router, projects.router], authenticated=False)

    with patch("utils.auth_service.ldap_authenticate", return_value=None):
        response = client.post(
            "/storage-pulse/api/users/login",
            json={"username": "alice", "password": "secret-password"},
        )

    assert response.status_code == 401
    assert "secret-password" not in response.text


def test_profile_and_business_api_require_token(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router, projects.router], authenticated=False)

    profile_response = client.get("/storage-pulse/api/users/current/profile")
    invalid_profile_response = client.get(
        "/storage-pulse/api/users/current/profile",
        headers={"Authorization": "Bearer invalid-token"},
    )
    users_response = client.get("/storage-pulse/api/users/")

    assert profile_response.status_code == 401
    assert invalid_profile_response.status_code == 401
    assert users_response.status_code == 401


def test_profile_reuses_authenticated_user_within_request(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router], authenticated=False)
    current_user = models.User(id=7, rd_username="alice", username="Alice Zhang")
    token = issue_token(current_user.id)

    with (
        patch("dependencies.decode_token", wraps=decode_token) as decode,
        patch("dependencies.usersCrud.get_user_by_id", return_value=current_user) as get_user,
    ):
        response = client.get(
            "/storage-pulse/api/users/current/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert (decode.call_count, get_user.call_count) == (1, 1)


def test_business_api_accepts_bearer_token_and_logout_returns_null_result(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router, projects.router], authenticated=False)

    with patch("utils.auth_service.ldap_authenticate", return_value=_profile("bob", "Bob Li", "bob@example.com")):
        login_response = client.post(
            "/storage-pulse/api/users/login",
            json={"username": "bob", "password": "secret-password"},
        )

    token = login_response.json()["result"]["token"]
    users_response = client.get(
        "/storage-pulse/api/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    projects_response = client.get(
        "/storage-pulse/api/projects/",
        headers={"Authorization": f"Bearer {token}"},
    )
    logout_response = client.post(
        "/storage-pulse/api/users/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert users_response.status_code == 403
    assert projects_response.status_code == 200
    assert logout_response.status_code == 200
    assert logout_response.json()["result"] is None


def test_logout_revokes_current_access_token(api_client_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router, projects.router], authenticated=False)

    with patch("utils.auth_service.ldap_authenticate", return_value=_profile("bob", "Bob Li", "bob@example.com")):
        login_response = client.post(
            "/storage-pulse/api/users/login",
            json={"username": "bob", "password": "secret-password"},
        )

    token = login_response.json()["result"]["token"]
    assert (
        client.get(
            "/storage-pulse/api/users/current/profile",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 200
    )

    logout_response = client.post(
        "/storage-pulse/api/users/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_after_logout = client.get(
        "/storage-pulse/api/users/current/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_response.status_code == 200
    assert profile_after_logout.status_code == 401


def test_login_and_logout_append_safe_unified_audit_results(api_client_factory, session_factory):
    base_config.set("jwt.secret_key", "test-secret")
    client = api_client_factory([users.router], authenticated=False)

    with patch("utils.auth_service.ldap_authenticate", return_value=_profile("bob", "Bob Li", "bob@example.com")):
        login_response = client.post(
            "/storage-pulse/api/users/login",
            json={"username": "bob", "password": "private-password"},
        )
    with patch("utils.auth_service.ldap_authenticate", return_value=None):
        rejected_response = client.post(
            "/storage-pulse/api/users/login",
            json={"username": "nobody", "password": "private-password"},
        )
    token = login_response.json()["result"]["token"]
    logout_response = client.post(
        "/storage-pulse/api/users/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert (login_response.status_code, rejected_response.status_code, logout_response.status_code) == (200, 401, 200)
    db = session_factory()
    try:
        events = db.query(models.AuditEvent).order_by(models.AuditEvent.occurred_at, models.AuditEvent.id).all()
    finally:
        db.close()
    assert [(event.action, event.outcome) for event in events] == [
        ("auth.login", "success"),
        ("auth.login", "denied"),
        ("auth.logout", "success"),
    ]
    assert all(event.phase == "result" for event in events)
    assert events[0].actor_user_id is not None
    assert events[1].actor_user_id is None
    serialized = json.dumps(
        [(event.before_summary, event.after_summary, event.event_metadata) for event in events],
        ensure_ascii=False,
    )
    assert "private-password" not in serialized
    assert token not in serialized
