# -*- coding: utf-8 -*-
import ssl
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from appConfig import base_config
import models
from routers import users
from schemas import usersSchema
from services import usersService
from utils import ldap_directory
from utils.security import issue_token


SYNC_PATH = "/storage-pulse/api/users/sync-ldap"


def _directory_user(rd_username, username=None, email=None, department=None):
    return {
        "username": rd_username,
        "display_name": username or rd_username,
        "email": email,
        "department": department,
        "user_dn": f"CN={rd_username},OU=Users,DC=example,DC=com",
        "matched_base": "OU=Users,DC=example,DC=com",
    }


def _seed_users(session_factory, *seeded_users):
    with session_factory() as db:
        db.add_all(seeded_users)
        db.commit()


def _database_snapshot(session_factory):
    with session_factory() as db:
        return [
            (
                user.id,
                user.rd_username,
                user.username,
                user.email,
                user.department,
                user.user_type,
                user.is_alert,
                user.quit_days,
            )
            for user in db.query(models.User).order_by(models.User.id).all()
        ]


def _client(api_client_factory, user_id):
    return api_client_factory(
        [users.router],
        authenticated=True,
        headers={"Authorization": f"Bearer {issue_token(user_id)}"},
    )


@pytest.fixture
def admin_api(api_client_factory, session_factory):
    base_config.set("jwt.secret_key", "test-jwt-secret-key-for-unit-tests-32")
    base_config.set("super_admin_usernames", ["admin"])
    _seed_users(
        session_factory,
        models.User(id=1, rd_username="admin", username="Admin", user_type=1),
    )
    return _client(api_client_factory, 1)


def test_ldap_directory_maps_configured_department_attribute():
    class Attribute:
        def __init__(self, value):
            self.value = value

    class Entry:
        entry_dn = "CN=Alice,OU=Users,DC=example,DC=com"
        sAMAccountName = Attribute("alice")
        cn = Attribute("Alice Zhang")
        mail = Attribute("alice@example.com")
        businessUnit = Attribute("Platform")

    class Connection:
        entries = [Entry()]

        def __init__(self):
            self.attributes = None

        def search(self, *, search_base, search_filter, attributes):
            self.attributes = attributes
            return True

        def unbind(self):
            pass

    connection = Connection()
    base_config.set("ldap.user_bases", ["OU=Users,DC=example,DC=com"])
    base_config.set("ldap.user_department_attribute", "businessUnit")

    result = ldap_directory.list_ldap_directory_users(bind_ldap=lambda: connection)

    assert "businessUnit" in connection.attributes
    assert result[0]["department"] == "Platform"


def test_ldap_directory_rejects_incomplete_multi_base_snapshot():
    class Connection:
        entries = []

        def search(self, *, search_base, search_filter, attributes):
            return search_base.endswith("Users,DC=example,DC=com")

        def unbind(self):
            pass

    base_config.set(
        "ldap.user_bases",
        ["OU=Users,DC=example,DC=com", "OU=Partners,DC=example,DC=com"],
    )

    with pytest.raises(RuntimeError, match="incomplete LDAP directory snapshot"):
        ldap_directory.list_ldap_directory_users(bind_ldap=Connection)


def test_sync_applies_all_user_lifecycle_rules(
    admin_api,
    session_factory,
    monkeypatch,
):
    _seed_users(
        session_factory,
        models.User(
            id=2,
            rd_username="active",
            username="Old Active",
            email="old-active@example.com",
            department="Legacy",
            user_type=2,
        ),
        models.User(
            id=3,
            rd_username="returning",
            username="Old Returning",
            user_type=0,
            quit_days=45,
        ),
        models.User(
            id=4,
            rd_username="public",
            username="Old Public",
            email="old-public@example.com",
            department="Shared",
            user_type=1,
        ),
        models.User(
            id=5,
            rd_username="blank-fields",
            username="Old Blank",
            email="keep@example.com",
            department="Keep Department",
            user_type=2,
        ),
        models.User(id=6, rd_username="missing", username="Missing", user_type=2),
    )
    snapshot = [
        _directory_user("new-user", "New User", "new@example.com", "New Department"),
        _directory_user("active", "Active User", "active@example.com", "Platform"),
        _directory_user("returning", "Returning User", "returning@example.com", "Platform"),
        _directory_user("public", "Public User", "public@example.com", "Public Department"),
        _directory_user("blank-fields", "Blank Fields", None, None),
    ]
    monkeypatch.setattr(ldap_directory, "list_ldap_directory_users", lambda: snapshot)

    response = admin_api.post(SYNC_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "ldap_total": 5,
        "created": 1,
        "updated": 3,
        "reactivated": 1,
        "marked_inactive": 1,
    }
    with session_factory() as db:
        by_name = {user.rd_username: user for user in db.query(models.User).all()}
        assert by_name["new-user"].user_type == 2
        assert (by_name["active"].username, by_name["active"].email, by_name["active"].department) == (
            "Active User",
            "active@example.com",
            "Platform",
        )
        assert (by_name["returning"].user_type, by_name["returning"].quit_days) == (2, 0)
        assert (
            by_name["public"].user_type,
            by_name["public"].username,
            by_name["public"].email,
            by_name["public"].department,
        ) == (1, "Public User", "public@example.com", "Public Department")
        assert (by_name["blank-fields"].email, by_name["blank-fields"].department) == (
            "keep@example.com",
            "Keep Department",
        )
        assert by_name["missing"].user_type == 0
        assert by_name["admin"].user_type == 1


def test_sync_matches_usernames_case_insensitively(
    admin_api,
    session_factory,
    monkeypatch,
):
    _seed_users(
        session_factory,
        models.User(
            id=2,
            rd_username="CaseUser",
            username="Old Name",
            email="old@example.com",
            user_type=2,
        ),
    )
    monkeypatch.setattr(
        ldap_directory,
        "list_ldap_directory_users",
        lambda: [_directory_user("caseuser", "Case User", "case@example.com", "Platform")],
    )

    response = admin_api.post(SYNC_PATH)

    assert response.status_code == 200
    with session_factory() as db:
        matched = [user for user in db.query(models.User).all() if user.rd_username.lower() == "caseuser"]
        assert len(matched) == 1
        assert matched[0].rd_username == "CaseUser"
        assert matched[0].email == "case@example.com"


@pytest.mark.parametrize("failure", ["empty", "incomplete"])
def test_unavailable_snapshot_returns_stable_503_without_writes(
    failure,
    admin_api,
    session_factory,
    monkeypatch,
):
    _seed_users(
        session_factory,
        models.User(id=2, rd_username="active", username="Active", user_type=2),
    )
    before = _database_snapshot(session_factory)

    if failure == "empty":
        monkeypatch.setattr(ldap_directory, "list_ldap_directory_users", lambda: [])
    else:
        def incomplete_snapshot():
            raise RuntimeError("incomplete LDAP directory snapshot: sensitive-base")

        monkeypatch.setattr(ldap_directory, "list_ldap_directory_users", incomplete_snapshot)

    response = admin_api.post(SYNC_PATH)

    assert response.status_code == 503
    assert response.json() == {"detail": "LDAP directory snapshot unavailable"}
    assert _database_snapshot(session_factory) == before


@pytest.mark.parametrize("conflict", ["ldap_case_duplicate", "local_case_duplicate"])
def test_username_conflicts_roll_back_all_changes(
    conflict,
    admin_api,
    session_factory,
    monkeypatch,
):
    if conflict == "local_case_duplicate":
        _seed_users(
            session_factory,
            models.User(id=2, rd_username="Duplicate", username="First", user_type=2),
            models.User(id=3, rd_username="duplicate", username="Second", user_type=2),
        )
        snapshot = [_directory_user("duplicate", "Changed", "changed@example.com", "New")]
    else:
        snapshot = [
            _directory_user("new-before-conflict", "New User"),
            _directory_user("Duplicate", "First"),
            _directory_user("duplicate", "Second"),
        ]
    before = _database_snapshot(session_factory)
    monkeypatch.setattr(ldap_directory, "list_ldap_directory_users", lambda: snapshot)

    response = admin_api.post(SYNC_PATH)

    assert response.status_code == 409
    assert _database_snapshot(session_factory) == before


def test_sync_requires_super_admin(api_client_factory, session_factory, monkeypatch):
    base_config.set("jwt.secret_key", "test-jwt-secret-key-for-unit-tests-32")
    base_config.set("super_admin_usernames", ["admin"])
    _seed_users(
        session_factory,
        models.User(id=2, rd_username="ordinary", username="Ordinary", user_type=2),
    )
    monkeypatch.setattr(
        ldap_directory,
        "list_ldap_directory_users",
        lambda: [_directory_user("ordinary")],
    )

    response = _client(api_client_factory, 2).post(SYNC_PATH)

    assert response.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "Missing Username", "email": "valid@example.com", "user_type": 2, "is_alert": True},
        {"rd_username": "   ", "username": "Blank Username", "user_type": 2, "is_alert": True},
        {"rd_username": "bad-email", "email": "not-an-email", "user_type": 2, "is_alert": True},
        {"rd_username": "bad-type", "email": "valid@example.com", "user_type": 3, "is_alert": True},
        {"rd_username": "bad-alert", "email": "valid@example.com", "user_type": 2, "is_alert": "yes"},
    ],
)
def test_manual_create_rejects_invalid_user_input(payload, admin_api):
    response = admin_api.post("/storage-pulse/api/users/", json=payload)

    assert response.status_code == 422


def test_manual_update_rejects_rd_username_change(admin_api, session_factory):
    _seed_users(
        session_factory,
        models.User(id=2, rd_username="fixed", username="Fixed", user_type=2),
    )

    response = admin_api.put(
        "/storage-pulse/api/users/2",
        json={
            "rd_username": "renamed",
            "username": "Fixed",
            "email": "fixed@example.com",
            "department": "Platform",
            "user_type": 2,
            "is_alert": True,
        },
    )

    assert response.status_code == 422


def test_manual_update_maintains_editable_user_fields(admin_api, session_factory):
    _seed_users(
        session_factory,
        models.User(
            id=2,
            rd_username="editable",
            username="Old Name",
            email="old@example.com",
            department="Old Department",
            user_type=2,
            is_alert=True,
        ),
    )

    response = admin_api.put(
        "/storage-pulse/api/users/2",
        json={
            "username": "New Name",
            "email": "new@example.com",
            "department": "New Department",
            "user_type": 1,
            "is_alert": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["department"] == "New Department"
    with session_factory() as db:
        updated = db.get(models.User, 2)
        assert (
            updated.rd_username,
            updated.username,
            updated.email,
            updated.department,
            updated.user_type,
            updated.is_alert,
        ) == (
            "editable",
            "New Name",
            "new@example.com",
            "New Department",
            1,
            False,
        )


def test_user_service_crud_success_conflict_and_not_found(admin_api):
    payload = {
        "rd_username": "service-user",
        "username": "Service User",
        "email": "service@example.com",
        "department": "Platform",
        "user_type": 2,
        "is_alert": True,
    }

    created = admin_api.post("/storage-pulse/api/users/", json=payload)
    duplicate = admin_api.post("/storage-pulse/api/users/", json=payload)
    listed = admin_api.get("/storage-pulse/api/users/", params={"nameLike": "service-user"})
    missing = admin_api.get("/storage-pulse/api/users/9999")
    deleted = admin_api.delete(f"/storage-pulse/api/users/{created.json()['id']}")

    assert created.status_code == 200
    assert duplicate.status_code == 409
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert missing.status_code == 404
    assert deleted.status_code == 204


def test_user_service_create_converts_integrity_error_without_transaction_control(monkeypatch):
    db = Mock()
    data = usersSchema.UserCreate(rd_username="conflict")
    monkeypatch.setattr(
        usersService.usersCrud,
        "get_user_by_rd_username_case_insensitive",
        lambda _db, _username: None,
    )

    def raise_integrity_error(_db, _data):
        raise IntegrityError("insert", {}, RuntimeError("duplicate"))

    monkeypatch.setattr(usersService.usersCrud, "create_user", raise_integrity_error)

    with pytest.raises(HTTPException) as error:
        usersService.create_user(db, data)

    assert error.value.status_code == 409
    db.rollback.assert_not_called()


def test_user_sync_converts_integrity_error_without_transaction_control(monkeypatch):
    db = Mock()
    db.flush.side_effect = IntegrityError("insert", {}, RuntimeError("duplicate"))
    monkeypatch.setattr(
        ldap_directory,
        "list_ldap_directory_users",
        lambda: [_directory_user("new-user")],
    )
    monkeypatch.setattr(usersService.usersCrud, "list_all_users", lambda _db: [])

    with pytest.raises(HTTPException) as error:
        usersService.sync_ldap_users(db)

    assert error.value.status_code == 409
    db.rollback.assert_not_called()


def test_ldap_config_defaults_and_secure_transport_variants(tmp_path):
    base_config.set("ldap.uri", "ldaps://dc.example.com")
    base_config.set("ldap.starttls", False)
    ldap_directory.require_secure_ldap_transport()

    base_config.set("ldap.uri", "")
    ldap_directory.require_secure_ldap_transport()

    base_config.set("ldap.bind_dn", "  CN=Service  ")
    base_config.set("ldap.bind_password", " direct-secret ")
    base_config.set("ldap.bind_password_file", None)
    base_config.set("ldap.ca_cert_path", str(tmp_path / "ca.pem"))
    base_config.set("ldap.user_department_attribute", "")

    assert ldap_directory.ldap_bind_dn() == "CN=Service"
    assert ldap_directory.ldap_bind_password() == "direct-secret"
    assert ldap_directory.ldap_ca_cert_path() == str(tmp_path / "ca.pem")
    assert ldap_directory.ldap_user_department_attribute() == "department"

    base_config.set("ldap.bind_password", "")
    base_config.set("ldap.bind_password_file", None)
    base_config.set("ldap.ca_cert_path", None)
    assert ldap_directory.ldap_bind_password() == ""
    assert ldap_directory.ldap_ca_cert_path() == ""


def test_ldap_server_requires_uri():
    base_config.set("ldap.uri", "")

    with pytest.raises(RuntimeError, match="missing ldap.uri"):
        ldap_directory._ldap_server()


@pytest.mark.parametrize("with_ca", [False, True])
def test_ldap_server_builds_optional_tls(monkeypatch, tmp_path, with_ca):
    created = {}

    class FakeTls:
        def __init__(self, **kwargs):
            created["tls_kwargs"] = kwargs

    class FakeServer:
        def __init__(self, url, **kwargs):
            created["url"] = url
            created["server_kwargs"] = kwargs

    base_config.set("ldap.uri", "ldaps://dc.example.com")
    base_config.set("ldap.starttls", False)
    base_config.set("ldap.ca_cert_path", str(tmp_path / "ca.pem") if with_ca else None)
    monkeypatch.setattr(
        ldap_directory,
        "_ldap_runtime_primitives",
        lambda: (
            FakeServer,
            object,
            FakeTls,
            {"ssl": ssl, "none": "NONE", "auto_bind_no_tls": "AUTO"},
        ),
    )

    server = ldap_directory._ldap_server()

    assert isinstance(server, FakeServer)
    assert created["url"] == "ldaps://dc.example.com"
    assert ("tls_kwargs" in created) is with_ca


def test_service_bind_requires_dn_and_password():
    base_config.set("ldap.bind_dn", "")
    base_config.set("ldap.bind_password", "secret")
    with pytest.raises(RuntimeError, match="missing ldap.bind_dn"):
        ldap_directory._service_bind_ldap()

    base_config.set("ldap.bind_dn", "CN=Service")
    base_config.set("ldap.bind_password", "")
    base_config.set("ldap.bind_password_file", None)
    with pytest.raises(RuntimeError, match="missing LDAP bind password"):
        ldap_directory._service_bind_ldap()


@pytest.mark.parametrize(
    ("start_tls_result", "bind_result", "expected_error"),
    [
        (False, True, "service bind start_tls rejected"),
        (True, False, "service bind rejected"),
        (True, True, None),
    ],
)
def test_service_bind_starttls_outcomes(
    monkeypatch,
    start_tls_result,
    bind_result,
    expected_error,
):
    class Connection:
        def __init__(self, *args, **kwargs):
            self.unbound = False

        def start_tls(self):
            return start_tls_result

        def bind(self):
            return bind_result

        def unbind(self):
            self.unbound = True

    base_config.set("ldap.bind_dn", "CN=Service")
    base_config.set("ldap.bind_password", "secret")
    base_config.set("ldap.starttls", True)
    monkeypatch.setattr(ldap_directory, "_ldap_server", lambda: object())
    monkeypatch.setattr(
        ldap_directory,
        "_ldap_runtime_primitives",
        lambda: (object, Connection, object, {"auto_bind_no_tls": "AUTO"}),
    )

    if expected_error:
        with pytest.raises(RuntimeError, match=expected_error):
            ldap_directory._service_bind_ldap()
    else:
        assert isinstance(ldap_directory._service_bind_ldap(), Connection)
