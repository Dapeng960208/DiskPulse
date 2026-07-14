# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from models import StorageUsage, User
from schemas import usersSchema
from utils.query import get_sort_column


def get_user_by_rd_username(db: Session, rd_username: str | None):
    if rd_username is None:
        return None
    return db.query(User).filter_by(rd_username=rd_username).first()


def get_user_by_rd_username_case_insensitive(db: Session, rd_username: str):
    return (
        db.query(User)
        .filter(func.lower(User.rd_username) == rd_username.lower())
        .first()
    )


def get_user_by_id(db: Session, id: int):
    return db.query(User).filter_by(id=id).first()


def create_user(db: Session, user: usersSchema.UserBase | usersSchema.UserCreate):
    user_db = User(
        email=user.email,
        username=user.username,
        rd_username=user.rd_username,
        avatar_url=user.avatar_url,
        department=user.department,
        iam_id=user.iam_id,
        user_type=user.user_type,
        is_alert=user.is_alert,
        updated_at=datetime.now(),
    )
    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    return user_db


def list_all_users(db: Session):
    return db.query(User).all()


def add_ldap_user(
    db: Session,
    *,
    rd_username: str,
    username: str,
    email: str | None,
    department: str | None,
):
    user = User(
        rd_username=rd_username,
        username=username,
        email=email,
        department=department,
        user_type=2,
        is_alert=True,
        quit_days=0,
        updated_at=datetime.now(),
    )
    db.add(user)
    return user


def apply_ldap_profile(
    user: User,
    *,
    username: str | None,
    email: str | None,
    department: str | None,
) -> None:
    if username:
        user.username = username
    if email:
        user.email = email
    if department:
        user.department = department
    user.updated_at = datetime.now()


def set_ldap_lifecycle(
    user: User,
    *,
    user_type: int,
    quit_days: int | None = None,
) -> None:
    user.user_type = user_type
    if quit_days is not None:
        user.quit_days = quit_days
    user.updated_at = datetime.now()


async def get_users(
    db: Session,
    page: int,
    size: int,
    nameLike: str | None = None,
    prop: str | None = None,
    order: str | None = None,
    user_type: int | None = None,
):
    query = db.query(User)
    if nameLike and len(nameLike.strip()) > 0:
        query = query.filter(or_(User.username.like(f"%{nameLike}%"), User.rd_username.like(f"%{nameLike}%")))
    if user_type is not None:
        query = query.filter(User.user_type == user_type)

    total = query.count()
    sort_column = get_sort_column(User, prop)
    if sort_column is not None:
        query = query.order_by(desc(sort_column) if order and order.lower() == "descending" else asc(sort_column))
    else:
        query = query.order_by(desc(User.storage_used))

    users = query.offset((page - 1) * size).limit(size).all()
    return users, total


def update_user(db: Session, user_id: int, user: usersSchema.UserUpdate):
    user_db = db.query(User).filter(User.id == user_id).first()
    if user_db is None:
        return None

    for field, value in user.model_dump(exclude_unset=True).items():
        setattr(user_db, field, value)
    user_db.updated_at = datetime.now()
    db.commit()
    db.refresh(user_db)
    return user_db


def delete_user_by_id(db: Session, user_id: int):
    db.query(StorageUsage).filter_by(user_id=user_id).delete()
    db.query(User).filter_by(id=user_id).delete()
    db.commit()
