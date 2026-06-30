# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from database import SessionLocal
from questdb.database import QuestDBSessionLocal, questdb_engine
from crud import usersCrud
from models import User
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
    "/storage-pulse/api/users/logout",
}


def _is_public_auth_request(request: Request) -> bool:
    return request.method.upper() == "OPTIONS" or request.url.path in PUBLIC_AUTH_PATHS


def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    token = parse_authorization_token(authorization)
    payload = decode_token(token, "access")
    user = usersCrud.get_user_by_id(request.state.db, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user is unavailable")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_authenticated_request(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> None:
    if _is_public_auth_request(request):
        return
    token = parse_authorization_token(authorization)
    payload = decode_token(token, "access")
    user = usersCrud.get_user_by_id(request.state.db, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user is unavailable")


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
