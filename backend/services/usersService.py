# -*- coding: utf-8 -*-
import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import usersCrud
from schemas import usersSchema
from utils import ldap_directory


logger = logging.getLogger("uvicorn.error")
SNAPSHOT_UNAVAILABLE_DETAIL = "LDAP directory snapshot unavailable"
USERNAME_CONFLICT_DETAIL = "LDAP username conflict"


def _normalized_username(value: str | None) -> str:
    return (value or "").strip().casefold()


def _snapshot_unavailable() -> HTTPException:
    logger.warning("LDAP directory snapshot unavailable")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=SNAPSHOT_UNAVAILABLE_DETAIL,
    )


def sync_ldap_users(db: Session) -> usersSchema.UserSyncResult:
    try:
        directory_users = ldap_directory.list_ldap_directory_users()
    except Exception as error:
        db.rollback()
        raise _snapshot_unavailable() from error
    if not directory_users:
        db.rollback()
        raise _snapshot_unavailable()

    try:
        existing_users = usersCrud.list_all_users(db)
        existing_by_username = {}
        for user in existing_users:
            normalized = _normalized_username(user.rd_username)
            if normalized and normalized in existing_by_username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=USERNAME_CONFLICT_DETAIL,
                )
            if normalized:
                existing_by_username[normalized] = user

        directory_by_username = {}
        for profile in directory_users:
            normalized = _normalized_username(profile.get("username"))
            if not normalized or normalized in directory_by_username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=USERNAME_CONFLICT_DETAIL,
                )
            directory_by_username[normalized] = profile

        created_users = 0
        updated_users = 0
        reactivated_users = 0
        marked_inactive_users = 0

        for normalized, profile in directory_by_username.items():
            user = existing_by_username.get(normalized)
            if user is None:
                usersCrud.add_ldap_user(
                    db,
                    rd_username=profile["username"].strip(),
                    username=(profile.get("display_name") or profile["username"]).strip(),
                    email=profile.get("email"),
                    department=profile.get("department"),
                )
                created_users += 1
                continue

            usersCrud.apply_ldap_profile(
                user,
                username=(profile.get("display_name") or "").strip() or None,
                email=(profile.get("email") or "").strip() or None,
                department=(profile.get("department") or "").strip() or None,
            )
            if user.user_type == 0:
                usersCrud.set_ldap_lifecycle(user, user_type=2, quit_days=0)
                reactivated_users += 1
            else:
                updated_users += 1

        directory_usernames = set(directory_by_username)
        for user in existing_users:
            if (
                user.user_type == 2
                and _normalized_username(user.rd_username) not in directory_usernames
            ):
                usersCrud.set_ldap_lifecycle(user, user_type=0)
                marked_inactive_users += 1

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=USERNAME_CONFLICT_DETAIL,
        ) from error
    except Exception:
        db.rollback()
        logger.error("LDAP user synchronization failed")
        raise

    return usersSchema.UserSyncResult(
        ldap_total=len(directory_users),
        created=created_users,
        updated=updated_users,
        reactivated=reactivated_users,
        marked_inactive=marked_inactive_users,
    )


def create_user(db: Session, data: usersSchema.UserCreate):
    if usersCrud.get_user_by_rd_username_case_insensitive(db, data.rd_username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The user exists")
    try:
        return usersCrud.create_user(db, data)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The user exists") from error


async def list_users(db: Session, **filters):
    return await usersCrud.get_users(db, **filters)


def get_user(db: Session, user_id: int):
    user = usersCrud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def update_user(db: Session, user_id: int, data: usersSchema.UserUpdate):
    get_user(db, user_id)
    return usersCrud.update_user(db, user_id=user_id, user=data)


def delete_user(db: Session, user_id: int) -> None:
    get_user(db, user_id)
    usersCrud.delete_user_by_id(db, user_id)
