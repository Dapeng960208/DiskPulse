# -*- coding: utf-8 -*-
from collections.abc import Callable
from pathlib import Path
from typing import Any
import os
import warnings

import yaml

from appConfig import base_config

DEFAULT_LDAP_USER_EXTRA_FILTERS = [
    "(!(objectClass=computer))",
    "(!(objectClass=group))",
]


def _config_value(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value is not None:
        return value
    configured = base_config.get(key, default)
    return str(configured) if configured is not None else default


def _config_bool(key: str, default: bool = False) -> bool:
    value = _config_value(key, "true" if default else "false")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _config_int(key: str, default: int) -> int:
    try:
        return int(_config_value(key, str(default)))
    except (TypeError, ValueError):
        return default


def _config_list(key: str, default: list[str] | None = None) -> list[str]:
    value = _config_value(key, "")
    if not value.strip():
        return list(default or [])
    if "\n" in value:
        items = []
        for line in value.splitlines():
            item = line.strip()
            if item.startswith("- "):
                item = item[2:].strip()
            if item:
                items.append(item)
        return items
    try:
        loaded = yaml.safe_load(value)
    except yaml.YAMLError:
        loaded = None
    if isinstance(loaded, list):
        return [str(item).strip() for item in loaded if str(item).strip()]
    if isinstance(loaded, str) and loaded.strip() != value.strip():
        return [loaded.strip()]
    return [item.strip() for item in value.split(";") if item.strip()]


def ldap_server_url() -> str:
    return _config_value("LDAP_SERVER_URL", _config_value("LDAP_URI", "")).strip()


def ldap_start_tls() -> bool:
    return _config_bool("LDAP_START_TLS")


def ldap_timeout_seconds() -> int:
    return _config_int("LDAP_TIMEOUT_SECONDS", 5)


def ldap_bind_dn() -> str:
    return _config_value("LDAP_BIND_DN").strip()


def ldap_bind_password() -> str:
    password = _config_value("LDAP_BIND_PASSWORD").strip()
    if password:
        return password
    password_file = _config_value("LDAP_BIND_PASSWORD_FILE").strip()
    if password_file:
        return Path(password_file).read_text(encoding="utf-8").strip()
    return ""


def ldap_ca_cert_path() -> str:
    return _config_value("LDAP_CA_CERT_PATH").strip()


def ldap_user_bases() -> list[str]:
    return _config_list("LDAP_USER_BASES")


def ldap_user_class() -> str:
    return _config_value("LDAP_USER_CLASS", "user").strip() or "user"


def ldap_user_name_attribute() -> str:
    return _config_value("LDAP_USER_NAME_ATTRIBUTE", "sAMAccountName").strip() or "sAMAccountName"


def ldap_user_fullname_attribute() -> str:
    return _config_value("LDAP_USER_FULLNAME_ATTRIBUTE", "cn").strip() or "cn"


def ldap_user_extra_filters() -> list[str]:
    return _config_list("LDAP_USER_EXTRA_FILTERS", DEFAULT_LDAP_USER_EXTRA_FILTERS)


def escape_ldap_filter_value(value: str) -> str:
    replacements = {
        "\\": r"\5c",
        "*": r"\2a",
        "(": r"\28",
        ")": r"\29",
        "\x00": r"\00",
    }
    return "".join(replacements.get(character, character) for character in value)


def build_ldap_user_search_filter(username: str | None = None) -> str:
    normalized_username = (username or "").strip()
    escaped_username = "*" if not normalized_username else escape_ldap_filter_value(normalized_username)
    extra_filters = "".join(ldap_user_extra_filters())
    return (
        f"(&(objectClass={ldap_user_class()})"
        f"{extra_filters}"
        f"({ldap_user_name_attribute()}={escaped_username}))"
    )


def _ldap_runtime_primitives() -> tuple[Any, Any, Any, dict[str, Any]]:
    try:
        import ssl

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"ldap3(\..*)?$")
            from ldap3 import ALL, AUTO_BIND_NO_TLS, Connection, Server, Tls
    except ImportError as error:  # pragma: no cover - runtime dependency
        raise RuntimeError("ldap3 is not installed") from error
    return Server, Connection, Tls, {"ssl": ssl, "all": ALL, "auto_bind_no_tls": AUTO_BIND_NO_TLS}


def _ldap_server() -> Any:
    server_url = ldap_server_url()
    if not server_url:
        raise RuntimeError("missing LDAP_SERVER_URL")

    Server, _Connection, Tls, constants = _ldap_runtime_primitives()
    tls = None
    ca_cert_path = ldap_ca_cert_path()
    if ca_cert_path:
        tls = Tls(ca_certs_file=ca_cert_path, validate=constants["ssl"].CERT_REQUIRED)
    return Server(
        server_url,
        connect_timeout=ldap_timeout_seconds(),
        get_info=constants["all"],
        tls=tls,
    )


def _service_bind_ldap() -> Any:
    bind_dn = ldap_bind_dn()
    bind_password = ldap_bind_password()
    if not bind_dn:
        raise RuntimeError("missing LDAP_BIND_DN")
    if not bind_password:
        raise RuntimeError("missing LDAP bind password")

    _Server, Connection, _Tls, constants = _ldap_runtime_primitives()
    connection = Connection(
        _ldap_server(),
        user=bind_dn,
        password=bind_password,
        auto_bind=False if ldap_start_tls() else constants["auto_bind_no_tls"],
        receive_timeout=ldap_timeout_seconds(),
    )
    if ldap_start_tls() and hasattr(connection, "start_tls") and not connection.start_tls():
        connection.unbind()
        raise RuntimeError("service bind start_tls rejected")
    if ldap_start_tls() and hasattr(connection, "bind") and not connection.bind():
        connection.unbind()
        raise RuntimeError("service bind rejected")
    return connection


def list_ldap_directory_users(
    username: str | None = None,
    *,
    bind_ldap: Callable[[], Any] | None = None,
    include_email: bool = True,
) -> list[dict[str, str | None]]:
    normalized_username = (username or "").strip()
    if username is not None and not normalized_username:
        return []

    attributes = [ldap_user_name_attribute(), ldap_user_fullname_attribute()]
    if include_email:
        attributes.append("mail")

    connection_factory = _service_bind_ldap if bind_ldap is None else bind_ldap
    connection = connection_factory()
    seen_usernames: set[str] = set()
    users: list[dict[str, str | None]] = []
    try:
        for base in ldap_user_bases():
            found = connection.search(
                search_base=base,
                search_filter=build_ldap_user_search_filter(normalized_username or None),
                attributes=attributes,
            )
            if not found:
                continue
            for entry in connection.entries:
                username_attr = getattr(entry, ldap_user_name_attribute(), None)
                entry_username = str(getattr(username_attr, "value", "") or normalized_username).strip()
                if not entry_username or entry_username in seen_usernames:
                    continue

                fullname_attr = getattr(entry, ldap_user_fullname_attribute(), None)
                display_name = str(getattr(fullname_attr, "value", "") or "").strip() or entry_username
                email_attr = getattr(entry, "mail", None)
                email = str(getattr(email_attr, "value", "") or "").strip() or None
                users.append(
                    {
                        "username": entry_username,
                        "display_name": display_name,
                        "email": email,
                        "user_dn": str(entry.entry_dn),
                        "matched_base": base,
                    }
                )
                seen_usernames.add(entry_username)
    finally:
        if hasattr(connection, "unbind"):
            connection.unbind()
    return users
