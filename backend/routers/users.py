# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from crud import usersCrud
from dependencies import get_db
from schemas import commonSchema, usersSchema

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=usersSchema.User)
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


@router.put("/{user_id}", response_model=usersSchema.User)
def update_user(user_id: int, user: usersSchema.UserUpdate, db: Session = Depends(get_db)):
    db_user = usersCrud.get_user_by_id(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return usersCrud.update_user(db, user_id=user_id, user=user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = usersCrud.get_user_by_id(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    usersCrud.delete_user_by_id(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
