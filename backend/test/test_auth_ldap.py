# -*- coding: utf-8 -*-
from unittest.mock import patch

import pytest

from appConfig import base_config


def test_ldap_user_search_filter_escapes_username():
    from utils.ldap_directory import build_ldap_user_search_filter

    base_config.set("ldap.user_class", "user")
    base_config.set("ldap.user_name_attribute", "sAMAccountName")

    search_filter = build_ldap_user_search_filter(r"alice*)(|(cn=*))\test")

    assert (
        search_filter
        == r"(&(objectClass=user)(!(objectClass=computer))(!(objectClass=group))"
        r"(sAMAccountName=alice\2a\29\28|\28cn=\2a\29\29\5ctest))"
    )


def test_list_ldap_directory_users_dedupes_and_normalizes_entries():
    from utils.ldap_directory import list_ldap_directory_users

    class FakeAttribute:
        def __init__(self, value):
            self.value = value

    class FakeEntry:
        def __init__(self, entry_dn, username, display_name, email):
            self.entry_dn = entry_dn
            self.sAMAccountName = FakeAttribute(username)
            self.cn = FakeAttribute(display_name)
            self.mail = FakeAttribute(email)

    class FakeConnection:
        def __init__(self):
            self.entries = []
            self.searches = []
            self.unbound = False

        def search(self, *, search_base, search_filter, attributes):
            self.searches.append((search_base, search_filter, attributes))
            if search_base == "OU=Users,DC=example,DC=com":
                self.entries = [
                    FakeEntry("CN=Alice,OU=Users,DC=example,DC=com", "alice", None, ""),
                    FakeEntry("CN=Bob,OU=Users,DC=example,DC=com", "bob", "Bob Li", "bob@example.com"),
                ]
                return True
            if search_base == "OU=Partners,DC=example,DC=com":
                self.entries = [
                    FakeEntry(
                        "CN=Alice,OU=Partners,DC=example,DC=com",
                        "alice",
                        "Alice Zhang",
                        "alice@example.com",
                    )
                ]
                return True
            return False

        def unbind(self):
            self.unbound = True

    connection = FakeConnection()
    base_config.set(
        "ldap.user_bases",
        ["OU=Users,DC=example,DC=com", "OU=Partners,DC=example,DC=com"],
    )
    base_config.set("ldap.user_name_attribute", "sAMAccountName")
    base_config.set("ldap.user_fullname_attribute", "cn")

    users = list_ldap_directory_users(bind_ldap=lambda: connection)

    assert users == [
        {
            "username": "alice",
            "display_name": "alice",
            "email": None,
            "user_dn": "CN=Alice,OU=Users,DC=example,DC=com",
            "matched_base": "OU=Users,DC=example,DC=com",
        },
        {
            "username": "bob",
            "display_name": "Bob Li",
            "email": "bob@example.com",
            "user_dn": "CN=Bob,OU=Users,DC=example,DC=com",
            "matched_base": "OU=Users,DC=example,DC=com",
        },
    ]
    assert connection.unbound is True
    assert (
        connection.searches[0][1]
        == "(&(objectClass=user)(!(objectClass=computer))(!(objectClass=group))(sAMAccountName=*))"
    )


def test_list_ldap_directory_users_rejects_blank_username():
    from utils.ldap_directory import list_ldap_directory_users

    assert list_ldap_directory_users("   ", bind_ldap=lambda: object()) == []


def test_targeted_ldap_user_search_skips_bases_without_a_match():
    from types import SimpleNamespace

    from utils.ldap_directory import list_ldap_directory_users

    class Connection:
        entries = []

        def search(self, *, search_base, search_filter, attributes):
            if search_base.startswith("OU=Partners"):
                self.entries = [
                    SimpleNamespace(
                        entry_dn="CN=Alice,OU=Partners,DC=example,DC=com",
                        sAMAccountName=SimpleNamespace(value="alice"),
                        cn=SimpleNamespace(value="Alice"),
                        mail=SimpleNamespace(value="alice@example.com"),
                    )
                ]
                return True
            self.entries = []
            return False

        def unbind(self):
            pass

    base_config.set(
        "ldap.user_bases",
        ["OU=Users,DC=example,DC=com", "OU=Partners,DC=example,DC=com"],
    )

    users = list_ldap_directory_users("alice", bind_ldap=Connection)

    assert [user["username"] for user in users] == ["alice"]


def test_plain_ldap_without_starttls_is_rejected():
    from utils.ldap_directory import require_secure_ldap_transport

    base_config.set("ldap.uri", "ldap://dc.example.com")
    base_config.set("ldap.starttls", False)

    with pytest.raises(RuntimeError, match="START_TLS must be enabled"):
        require_secure_ldap_transport()


def test_bind_password_file_is_relative_to_config(tmp_path):
    from utils.ldap_directory import ldap_bind_password

    password_file = tmp_path / "ldap-password.dev"
    password_file.write_text("file-secret\n", encoding="utf-8")
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
ldap:
  bind_password_file: ./ldap-password.dev
  lookup_user_dn: true
  lookup_as_user: false
""".strip(),
        encoding="utf-8",
    )
    base_config.load(config_file)

    assert ldap_bind_password() == "file-secret"


def test_bind_ldap_user_starts_tls_before_user_bind():
    from utils import auth_service

    events = []

    class FakeConnection:
        bound = False

        def __init__(self, server, user=None, password=None, auto_bind=False, receive_timeout=None):
            events.append("connect")
            self.user = user
            self.password = password

        def start_tls(self):
            events.append("start_tls")
            return True

        def bind(self):
            events.append(f"bind:{self.user}:{self.password}")
            self.bound = True
            return True

        def unbind(self):
            events.append("unbind")
            self.bound = False

    base_config.set("ldap.uri", "ldap://dc.example.com")
    base_config.set("ldap.starttls", True)
    base_config.set("ldap.timeout_seconds", 5)
    with patch.object(auth_service, "_ldap_server", lambda: object()):
        with patch.object(
            auth_service,
            "_ldap_runtime_primitives",
            lambda: (object, FakeConnection, object, {"auto_bind_no_tls": object()}),
        ):
            assert auth_service._bind_ldap_user("CN=Root Admin,OU=Users,DC=example,DC=com", "secret") is True

    assert events == [
        "connect",
        "start_tls",
        "bind:CN=Root Admin,OU=Users,DC=example,DC=com:secret",
        "unbind",
    ]


def test_bind_ldap_user_logs_safe_rejection_reason(caplog):
    from utils import auth_service

    class FakeConnection:
        bound = False
        result = {"result": 49, "description": "invalidCredentials"}

        def __init__(self, server, user=None, password=None, auto_bind=False, receive_timeout=None):
            pass

        def start_tls(self):
            return True

        def bind(self):
            return False

        def unbind(self):
            pass

    base_config.set("ldap.uri", "ldap://dc.example.com")
    base_config.set("ldap.starttls", True)
    caplog.set_level("WARNING", logger="uvicorn.error")
    with patch.object(auth_service, "_ldap_server", lambda: object()):
        with patch.object(
            auth_service,
            "_ldap_runtime_primitives",
            lambda: (object, FakeConnection, object, {"auto_bind_no_tls": object()}),
        ):
            assert auth_service._bind_ldap_user("CN=Root Admin,OU=Users,DC=example,DC=com", "secret") is False

    assert "LDAP user bind rejected: result=49 description=invalidCredentials" in caplog.text
    assert caplog.records[-1].name == "uvicorn.error"
    assert "CN=Root Admin" not in caplog.text
    assert "secret" not in caplog.text


def test_ldap_authenticate_logs_when_directory_user_is_not_found(caplog):
    from utils import auth_service

    base_config.set("ldap.uri", "ldap://dc.example.com")
    base_config.set("ldap.user_bases", ["OU=Users,DC=example,DC=com"])
    caplog.set_level("WARNING", logger="uvicorn.error")
    with patch.object(auth_service, "_iter_ldap_users", lambda username: iter(())):
        assert auth_service.ldap_authenticate("missing-user", "secret") is None

    assert "LDAP authentication failed: directory user not found" in caplog.text
    assert "missing-user" not in caplog.text
    assert "secret" not in caplog.text
