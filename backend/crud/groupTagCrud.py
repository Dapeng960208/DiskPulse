# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session

from models import Group, GroupTag


def get_group_tag(db: Session, group_tag_id: int) -> GroupTag | None:
    return db.get(GroupTag, group_tag_id)


def get_group_tag_by_name(
    db: Session,
    name: str,
    *,
    exclude_id: int | None = None,
) -> GroupTag | None:
    query = db.query(GroupTag).filter(GroupTag.name == name)
    if exclude_id is not None:
        query = query.filter(GroupTag.id != exclude_id)
    return query.first()


def list_group_tags(
    db: Session,
    *,
    page: int,
    size: int,
) -> tuple[list[GroupTag], int]:
    query = db.query(GroupTag)
    return (
        query.order_by(GroupTag.name.asc()).offset((page - 1) * size).limit(size).all(),
        query.count(),
    )


def has_linked_group(db: Session, group_tag_id: int) -> bool:
    return db.query(Group.id).filter(Group.group_tag_id == group_tag_id).first() is not None
