# -*- coding: utf-8 -*-
import pytest
from fastapi import HTTPException

from models import Project, User
from services.project_access_service import (
    ensure_reader_membership,
    require_project_permission,
    set_project_member,
)


def _user(username: str) -> User:
    return User(rd_username=username, username=username)


def _project(name: str) -> Project:
    return Project(name=name)


def test_collection_reader_membership_is_idempotent_and_never_downgrades(db_session):
    user = _user("collector-user")
    project = _project("project-a")
    db_session.add_all([user, project])
    db_session.commit()

    created = ensure_reader_membership(db_session, user_id=user.id, project_id=project.id)
    repeated = ensure_reader_membership(db_session, user_id=user.id, project_id=project.id)
    assert created.role == "reader"
    assert repeated.id == created.id

    elevated = set_project_member(
        db_session,
        project_id=project.id,
        user_id=user.id,
        role="editor",
        actor_is_super_admin=True,
    )
    unchanged = ensure_reader_membership(db_session, user_id=user.id, project_id=project.id)
    assert elevated.role == "editor"
    assert unchanged.role == "editor"


def test_project_role_cannot_read_another_project(db_session):
    user = _user("project-reader")
    allowed_project = _project("allowed-project")
    other_project = _project("other-project")
    db_session.add_all([user, allowed_project, other_project])
    db_session.commit()
    ensure_reader_membership(db_session, user_id=user.id, project_id=allowed_project.id)

    require_project_permission(db_session, user, allowed_project.id, "reader")
    with pytest.raises(HTTPException) as error:
        require_project_permission(db_session, user, other_project.id, "reader")
    assert error.value.status_code == 403
