# -*- coding: utf-8 -*-
from unittest.mock import patch

from appConfig import base_config
import models  # noqa: F401
from routers import projects, users
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
    logout_response = client.post(
        "/storage-pulse/api/users/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert users_response.status_code == 200
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
