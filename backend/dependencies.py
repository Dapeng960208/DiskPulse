# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from database import SessionLocal
from questdb.database import QuestDBSessionLocal, questdb_engine
from crud import usersCrud
from models import User
from utils.auth_service import is_super_admin
from utils.security import decode_token, parse_authorization_token


class DBSession:
    def __enter__(self):
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()


def get_db(request: Request):
    return request.state.db


PUBLIC_AUTH_PATHS = {
    "/storage-pulse/api/users/login",
}


def _is_public_auth_request(request: Request) -> bool:
    return request.method.upper() == "OPTIONS" or request.url.path in PUBLIC_AUTH_PATHS


def _resolve_current_user(request: Request, authorization: str | None) -> User:
    current_user = getattr(request.state, "current_user", None)
    if current_user is not None:
        return current_user

    token = parse_authorization_token(authorization)
    payload = decode_token(token, "access")
    current_user = usersCrud.get_user_by_id(request.state.db, int(payload["sub"]))
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user is unavailable")
    request.state.current_user = current_user
    return current_user


def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    return _resolve_current_user(request, authorization)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_current_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    return parse_authorization_token(authorization)


CurrentTokenDep = Annotated[str, Depends(get_current_token)]


def require_super_admin(current_user: CurrentUserDep) -> None:
    if not is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super admin permission required")


def require_authenticated_request(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> None:
    if _is_public_auth_request(request):
        return
    _resolve_current_user(request, authorization)


class QuestDBSession:
    def __init__(self, config=None):
        self.config = config

    def __enter__(self):
        self.quest_db = QuestDBSessionLocal()
        return self.quest_db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quest_db.close()


def get_questdb_session():
    return QuestDBSessionLocal()


def get_questdb_engine():
    return questdb_engine
