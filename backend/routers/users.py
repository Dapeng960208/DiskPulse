# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from dependencies import (
    CurrentTokenDep,
    CurrentUserDep,
    get_db,
    require_authenticated_request,
    require_super_admin,
)
from schemas import commonSchema, usersSchema
from services import usersService
from utils.auth_service import build_frontend_profile, login_user
from utils.security import revoke_token

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_authenticated_request)],
)
DBDep = Annotated[Session, Depends(get_db)]
AdminDep = Annotated[None, Depends(require_super_admin)]


@router.post("/login")
def login(payload: usersSchema.LoginIn, db: DBDep) -> dict:
    return {
        "result": login_user(
            db,
            username=payload.username,
            password=payload.password,
        )
    }


@router.post("/logout")
def logout(token: CurrentTokenDep) -> dict:
    revoke_token(token)
    return {"result": None}


@router.get("/current/profile")
def current_profile(current_user: CurrentUserDep) -> dict:
    return {"result": build_frontend_profile(current_user)}


@router.post("/sync-ldap", response_model=usersSchema.UserSyncResult)
def sync_ldap_users(_admin: AdminDep, db: DBDep):
    return usersService.sync_ldap_users(db)


@router.post("/", response_model=usersSchema.User)
def create_user(user: usersSchema.UserCreate, _admin: AdminDep, db: DBDep):
    return usersService.create_user(db, user)


@router.get("/", response_model=commonSchema.ResponseModel)
async def read_users(
    db: DBDep,
    page: int = 1,
    size: int = 20,
    nameLike: str | None = None,
    user_type: int | None = None,
    prop: str | None = None,
    order: str | None = None,
    load_detail: bool = Query(True),
):
    users, total = await usersService.list_users(
        db,
        page=page,
        size=size,
        nameLike=nameLike,
        prop=prop,
        order=order,
        user_type=user_type,
    )
    if load_detail is False:
        return commonSchema.ResponseModel[usersSchema.OnlyUser](content=users, total=total)
    return commonSchema.ResponseModel[usersSchema.User](content=users, total=total)


@router.get("/{user_id}", response_model=usersSchema.User)
def read_user(user_id: int, db: DBDep):
    return usersService.get_user(db, user_id)


@router.put("/{user_id}", response_model=usersSchema.User)
def update_user(
    user_id: int,
    user: usersSchema.UserUpdate,
    _admin: AdminDep,
    db: DBDep,
):
    return usersService.update_user(db, user_id, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, _admin: AdminDep, db: DBDep):
    usersService.delete_user(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
