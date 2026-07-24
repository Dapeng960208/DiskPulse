# -*- coding: utf-8 -*-
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from appConfig import base_config
from crud import usersCrud
from models import User
from utils import ldap_directory
from utils.ldap_directory import (
    _ldap_runtime_primitives,
    _ldap_server,
    ldap_server_url,
    ldap_start_tls,
    ldap_timeout_seconds,
    ldap_user_bases,
    list_ldap_directory_users,
)
from utils.security import issue_token
from utils.datetime_utils import utc_now


SUPERADMIN_ROLE = "superadmin"
SUPERADMIN_PERMISSION = ["*", "*", "*"]
logger = logging.getLogger("uvicorn.error")


def is_super_admin(user: User) -> bool:
    rd_username = user.rd_username or user.username or ""
    return rd_username in set(base_config.get("super_admin_usernames", []))


def _iter_ldap_users(username: str):
    for candidate in list_ldap_directory_users(username, include_email=True):
        yield {
            "username": candidate["username"],
            "user_dn": candidate["user_dn"],
            "display_name": candidate["display_name"],
            "email": candidate.get("email"),
            "matched_base": candidate["matched_base"],
        }


def _bind_ldap_user(user_dn: str, password: str) -> bool:
    if not password:
        return False

    _Server, Connection, _Tls, constants = _ldap_runtime_primitives()
    connection = None
    try:
        connection = Connection(
            _ldap_server(),
            user=user_dn,
            password=password,
            auto_bind=False if ldap_start_tls() else constants["auto_bind_no_tls"],
            receive_timeout=ldap_timeout_seconds(),
        )
        if ldap_start_tls() and hasattr(connection, "start_tls") and not connection.start_tls():
            result = getattr(connection, "result", {}) or {}
            logger.warning(
                "LDAP user STARTTLS rejected: result=%s description=%s",
                result.get("result"),
                result.get("description"),
            )
            return False
        if ldap_start_tls() and hasattr(connection, "bind") and not connection.bind():
            result = getattr(connection, "result", {}) or {}
            logger.warning(
                "LDAP user bind rejected: result=%s description=%s",
                result.get("result"),
                result.get("description"),
            )
            return False
        return bool(getattr(connection, "bound", True))
    except Exception as error:
        logger.warning("LDAP user bind failed: exception=%s", type(error).__name__)
        return False
    finally:
        if connection is not None and hasattr(connection, "unbind"):
            connection.unbind()


def ldap_authenticate(username: str, password: str) -> dict | None:
    if not ldap_server_url() or not ldap_user_bases():
        return None

    normalized = username.strip()
    if not normalized or not password:
        return None

    found_directory_user = False
    for candidate in _iter_ldap_users(normalized):
        found_directory_user = True
        if _bind_ldap_user(str(candidate["user_dn"]), password):
            profile = {
                "username": candidate["username"],
                "display_name": candidate["display_name"],
                "user_dn": candidate["user_dn"],
                "matched_base": candidate["matched_base"],
            }
            email = candidate.get("email")
            if email:
                profile["email"] = email
            return profile
    if not found_directory_user:
        logger.warning("LDAP authentication failed: directory user not found")
    return None


def upsert_user_from_ldap_profile(db: Session, profile: dict) -> User:
    rd_username = str(profile["username"]).strip()
    if not rd_username:
        raise ValueError("LDAP username must not be empty")

    user = usersCrud.get_user_by_rd_username(db, rd_username)
    display_name = str(profile.get("display_name") or rd_username).strip() or rd_username
    email = str(profile.get("email") or "").strip() or None
    if user is None:
        user = User(
            rd_username=rd_username,
            username=display_name,
            email=email,
            user_type=2,
            is_alert=True,
            updated_at=utc_now(),
        )
        db.add(user)
    else:
        user.username = display_name
        if email:
            user.email = email
        if user.user_type is None:
            user.user_type = 2
        user.updated_at = utc_now()

    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, *, username: str, password: str) -> dict[str, str]:
    profile = ldap_authenticate(username, password)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    user = upsert_user_from_ldap_profile(db, profile)
    return {"token": issue_token(user.id, "access"), "token_type": "bearer"}


def build_frontend_profile(user: User) -> dict:
    rd_username = user.rd_username or user.username or ""
    common_name = user.username or user.rd_username or ""
    role_codes: list[str] = []
    permission_codes: list[list[str]] = []
    if is_super_admin(user):
        role_codes = [SUPERADMIN_ROLE]
        permission_codes = [SUPERADMIN_PERMISSION]

    return {
        "id": user.id,
        "avatarUrl": user.avatar_url or "",
        "commonName": common_name,
        "roleCodes": role_codes,
        "permissionCodes": permission_codes,
        "extensionAttributes": {"rdUsername": rd_username},
        "time_zone": user.time_zone,
    }


# Re-exported for tests and patching.
build_ldap_user_search_filter = ldap_directory.build_ldap_user_search_filter
