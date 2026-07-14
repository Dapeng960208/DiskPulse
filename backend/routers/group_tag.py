# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db, require_super_admin
from schemas import groupTagSchema
from services import groupTagService


router = APIRouter(prefix="/group-tags", tags=["group-tags"])
DBDep = Annotated[Session, Depends(get_db)]
AdminDep = Annotated[None, Depends(require_super_admin)]


@router.get("", response_model=groupTagSchema.GroupTagPage)
def list_group_tags(
    _current_user: CurrentUserDep,
    db: DBDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return groupTagService.list_group_tags(db, page=page, size=size)


@router.post("", response_model=groupTagSchema.GroupTag, status_code=status.HTTP_201_CREATED)
def create_group_tag(data: groupTagSchema.GroupTagWrite, _admin: AdminDep, db: DBDep):
    return groupTagService.create_group_tag(db, data=data)


@router.get("/{group_tag_id}", response_model=groupTagSchema.GroupTag)
def get_group_tag(group_tag_id: int, _current_user: CurrentUserDep, db: DBDep):
    return groupTagService.get_group_tag(db, group_tag_id=group_tag_id)


@router.put("/{group_tag_id}", response_model=groupTagSchema.GroupTag)
def update_group_tag(
    group_tag_id: int,
    data: groupTagSchema.GroupTagWrite,
    _admin: AdminDep,
    db: DBDep,
):
    return groupTagService.update_group_tag(db, group_tag_id=group_tag_id, data=data)


@router.delete("/{group_tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group_tag(group_tag_id: int, _admin: AdminDep, db: DBDep):
    groupTagService.delete_group_tag(db, group_tag_id=group_tag_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
