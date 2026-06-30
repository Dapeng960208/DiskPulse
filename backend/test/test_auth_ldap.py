# -*- coding: utf-8 -*-
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class LdapDirectoryTest(unittest.TestCase):
    def test_ldap_user_search_filter_escapes_username(self):
        from utils.ldap_directory import build_ldap_user_search_filter

        with patch.dict(
            os.environ,
            {
                "LDAP_USER_CLASS": "user",
                "LDAP_USER_NAME_ATTRIBUTE": "sAMAccountName",
            },
            clear=False,
        ):
            search_filter = build_ldap_user_search_filter(r"alice*)(|(cn=*))\test")

        self.assertEqual(
            search_filter,
            r"(&(objectClass=user)(!(objectClass=computer))(!(objectClass=group))"
            r"(sAMAccountName=alice\2a\29\28|\28cn=\2a\29\29\5ctest))",
        )

    def test_list_ldap_directory_users_dedupes_and_normalizes_entries(self):
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
        with patch.dict(
            os.environ,
            {
                "LDAP_USER_BASES": "OU=Users,DC=example,DC=com\nOU=Partners,DC=example,DC=com",
                "LDAP_USER_NAME_ATTRIBUTE": "sAMAccountName",
                "LDAP_USER_FULLNAME_ATTRIBUTE": "cn",
            },
            clear=False,
        ):
            users = list_ldap_directory_users(bind_ldap=lambda: connection)

        self.assertEqual(
            users,
            [
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
            ],
        )
        self.assertTrue(connection.unbound)
        self.assertEqual(
            connection.searches[0][1],
            "(&(objectClass=user)(!(objectClass=computer))(!(objectClass=group))(sAMAccountName=*))",
        )

    def test_list_ldap_directory_users_rejects_blank_username(self):
        from utils.ldap_directory import list_ldap_directory_users

        self.assertEqual(list_ldap_directory_users("   ", bind_ldap=lambda: object()), [])

    def test_bind_ldap_user_starts_tls_before_user_bind(self):
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

        with patch.dict(
            os.environ,
            {
                "LDAP_SERVER_URL": "ldap://dc.example.com",
                "LDAP_START_TLS": "true",
                "LDAP_TIMEOUT_SECONDS": "5",
            },
            clear=False,
        ):
            with patch.object(auth_service, "_ldap_server", lambda: object()):
                with patch.object(
                    auth_service,
                    "_ldap_runtime_primitives",
                    lambda: (object, FakeConnection, object, {"auto_bind_no_tls": object()}),
                ):
                    self.assertTrue(
                        auth_service._bind_ldap_user(
                            "CN=Root Admin,OU=Users,DC=example,DC=com",
                            "secret",
                        )
                    )

        self.assertEqual(
            events,
            [
                "connect",
                "start_tls",
                "bind:CN=Root Admin,OU=Users,DC=example,DC=com:secret",
                "unbind",
            ],
        )


if __name__ == "__main__":
    unittest.main()
