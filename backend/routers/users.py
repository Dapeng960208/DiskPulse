# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from crud import usersCrud
from dependencies import CurrentTokenDep, CurrentUserDep, get_db, require_authenticated_request, require_super_admin
from schemas import commonSchema, usersSchema
from utils.auth_service import build_frontend_profile, login_user
from utils.security import revoke_token

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_authenticated_request)],
)


@router.post("/login")
def login(payload: usersSchema.LoginIn, db: Session = Depends(get_db)) -> dict:
    return {"result": login_user(db, username=payload.username, password=payload.password)}


@router.post("/logout")
def logout(token: CurrentTokenDep) -> dict:
    revoke_token(token)
    return {"result": None}


@router.get("/current/profile")
def current_profile(current_user: CurrentUserDep) -> dict:
    return {"result": build_frontend_profile(current_user)}


@router.post("/", response_model=usersSchema.User, dependencies=[Depends(require_super_admin)])
def create_user(user: usersSchema.UserBase, db: Session = Depends(get_db)):
    user_db = usersCrud.get_user_by_rd_username(db, rd_username=user.rd_username)
    if user_db is not None:
        raise HTTPException(status_code=400, detail="The user exists")
    return usersCrud.create_user(db=db, user=user)


@router.get("/", response_model=commonSchema.ResponseModel)
async def read_users(
    page: int = 1,
    size: int = 20,
    nameLike: str | None = None,
    user_type: int | None = None,
    prop: str | None = None,
    order: str | None = None,
    load_detail: bool = Query(True),
    db: Session = Depends(get_db),
):
    users, total = await usersCrud.get_users(
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
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = usersCrud.get_user_by_id(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=usersSchema.User, dependencies=[Depends(require_super_admin)])
def update_user(user_id: int, user: usersSchema.UserUpdate, db: Session = Depends(get_db)):
    db_user = usersCrud.get_user_by_id(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return usersCrud.update_user(db, user_id=user_id, user=user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_super_admin)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = usersCrud.get_user_by_id(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    usersCrud.delete_user_by_id(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
