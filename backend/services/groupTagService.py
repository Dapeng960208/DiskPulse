# -*- coding: utf-8 -*-
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import groupTagCrud
from models import GroupTag
from schemas import groupTagSchema


def _get_group_tag(db: Session, group_tag_id: int) -> GroupTag:
    group_tag = groupTagCrud.get_group_tag(db, group_tag_id)
    if group_tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group tag not found")
    return group_tag


def list_group_tags(db: Session, *, page: int, size: int) -> dict:
    tags, total = groupTagCrud.list_group_tags(db, page=page, size=size)
    return {"content": tags, "total": total}


def get_group_tag(db: Session, *, group_tag_id: int) -> GroupTag:
    return _get_group_tag(db, group_tag_id)


def create_group_tag(db: Session, *, data: groupTagSchema.GroupTagWrite) -> GroupTag:
    if groupTagCrud.get_group_tag_by_name(db, data.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group tag name already exists")
    group_tag = GroupTag(name=data.name)
    try:
        db.add(group_tag)
        db.commit()
        db.refresh(group_tag)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group tag name already exists") from error
    except Exception:
        db.rollback()
        raise
    return group_tag


def update_group_tag(
    db: Session,
    *,
    group_tag_id: int,
    data: groupTagSchema.GroupTagWrite,
) -> GroupTag:
    group_tag = _get_group_tag(db, group_tag_id)
    if groupTagCrud.get_group_tag_by_name(db, data.name, exclude_id=group_tag_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group tag name already exists")
    group_tag.name = data.name
    try:
        db.commit()
        db.refresh(group_tag)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group tag name already exists") from error
    except Exception:
        db.rollback()
        raise
    return group_tag


def delete_group_tag(db: Session, *, group_tag_id: int) -> None:
    group_tag = _get_group_tag(db, group_tag_id)
    if groupTagCrud.has_linked_group(db, group_tag_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group tag has linked group")
    try:
        db.delete(group_tag)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group tag has linked group") from error
    except Exception:
        db.rollback()
        raise
