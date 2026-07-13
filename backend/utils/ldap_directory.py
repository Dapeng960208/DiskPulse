# -*- coding: utf-8 -*-
from collections.abc import Callable
from typing import Any
import warnings

from appConfig import base_config

DEFAULT_LDAP_USER_EXTRA_FILTERS = [
    "(!(objectClass=computer))",
    "(!(objectClass=group))",
]


def ldap_server_url() -> str:
    return str(base_config.get("ldap.uri", "")).strip()


def ldap_start_tls() -> bool:
    return base_config.get("ldap.starttls", False) is True


def require_secure_ldap_transport() -> None:
    server_url = ldap_server_url().lower()
    if server_url.startswith("ldaps://") or ldap_start_tls():
        return
    if server_url:
        raise RuntimeError("LDAP_START_TLS must be enabled for ldap:// servers")


def ldap_timeout_seconds() -> int:
    return base_config.get("ldap.timeout_seconds", 5)


def ldap_bind_dn() -> str:
    return str(base_config.get("ldap.bind_dn", "")).strip()


def ldap_bind_password() -> str:
    password = str(base_config.get("ldap.bind_password", "")).strip()
    if password:
        return password
    password_file = base_config.resolve_path("ldap.bind_password_file")
    if password_file:
        return password_file.read_text(encoding="utf-8").strip()
    return ""


def ldap_ca_cert_path() -> str:
    path = base_config.resolve_path("ldap.ca_cert_path")
    return str(path) if path else ""


def ldap_user_bases() -> list[str]:
    return base_config.get("ldap.user_bases", [])


def ldap_user_class() -> str:
    return str(base_config.get("ldap.user_class", "user")).strip() or "user"


def ldap_user_name_attribute() -> str:
    return str(base_config.get("ldap.user_name_attribute", "sAMAccountName")).strip() or "sAMAccountName"


def ldap_user_fullname_attribute() -> str:
    return str(base_config.get("ldap.user_fullname_attribute", "cn")).strip() or "cn"


def ldap_user_extra_filters() -> list[str]:
    return base_config.get("ldap.user_extra_filters", DEFAULT_LDAP_USER_EXTRA_FILTERS)


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
        raise RuntimeError("missing ldap.uri")
    require_secure_ldap_transport()

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
        raise RuntimeError("missing ldap.bind_dn")
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
