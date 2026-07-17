# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from dependencies import (
    CurrentTokenDep,
    CurrentUserDep,
    get_db,
    require_authenticated_request,
    require_super_admin,
)
from schemas import commonSchema, usersSchema
from services import audit_service, usersService
from utils.auth_service import build_frontend_profile, login_user
from utils.security import decode_token, revoke_token

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_authenticated_request)],
)
DBDep = Annotated[Session, Depends(get_db)]
AdminDep = Annotated[None, Depends(require_super_admin)]


@router.post("/login")
def login(payload: usersSchema.LoginIn, request: Request, db: DBDep) -> dict:
    try:
        result = login_user(
            db,
            username=payload.username,
            password=payload.password,
        )
    except HTTPException:
        audit_service.append_audit_event(
            db,
            context=audit_service.audit_context_for_request(request, actor_user_id=None),
            phase="result",
            action="auth.login",
            resource_type="user",
            outcome="denied",
            reason_code="invalid_credentials",
        )
        db.commit()
        raise

    actor_user_id = int(decode_token(result["token"])["sub"])
    audit_service.append_audit_event(
        db,
        context=audit_service.audit_context_for_request(request, actor_user_id=actor_user_id),
        phase="result",
        action="auth.login",
        resource_type="user",
        resource_id=actor_user_id,
        outcome="success",
    )
    db.commit()
    return {"result": result}


@router.post("/logout")
def logout(token: CurrentTokenDep, request: Request, current_user: CurrentUserDep, db: DBDep) -> dict:
    revoke_token(token)
    audit_service.append_audit_event(
        db,
        context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        phase="result",
        action="auth.logout",
        resource_type="user",
        resource_id=current_user.id,
        outcome="success",
    )
    db.commit()
    return {"result": None}


@router.get("/current/profile")
def current_profile(current_user: CurrentUserDep) -> dict:
    return {"result": build_frontend_profile(current_user)}


@router.post("/sync-ldap", response_model=usersSchema.UserSyncResult)
def sync_ldap_users(_admin: AdminDep, db: DBDep):
    return usersService.sync_ldap_users(db)


@router.post(
    "/",
    response_model=usersSchema.User,
)
def create_user(user: usersSchema.UserCreate, _admin: AdminDep, db: DBDep):
    return usersService.create_user(db, user)


@router.get(
    "/",
    response_model=commonSchema.ResponseModel,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "list_users",
        "ai_description": "分页查询用户",
    },
)
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


@router.get(
    "/{user_id}",
    response_model=usersSchema.User,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_user",
        "ai_description": "查询指定用户",
    },
)
def read_user(user_id: int, db: DBDep):
    return usersService.get_user(db, user_id)


@router.put(
    "/{user_id}",
    response_model=usersSchema.User,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "update_user",
        "ai_description": "更新用户",
    },
)
def update_user(
    user_id: int,
    user: usersSchema.UserUpdate,
    _admin: AdminDep,
    db: DBDep,
):
    return usersService.update_user(db, user_id, user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(user_id: int, _admin: AdminDep, db: DBDep):
    usersService.delete_user(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
