# -*- coding: utf-8 -*-
import pytest
from fastapi import HTTPException

from models import Group, Project, StorageUsage, User
from services.project_access_service import (
    ensure_reader_membership,
    group_capabilities,
    require_project_permission,
    set_project_member,
    storage_usage_capabilities,
)
from appConfig import base_config


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


def test_quota_capabilities_limit_groups_to_super_admins_and_users_to_project_owners():
    base_config.set("super_admin_usernames", ["super-admin"])
    group_owner = _user("group-owner")
    project_owner = _user("project-owner")
    super_admin = _user("super-admin")
    project = Project(id=1, name="project-a", in_charge_user_id=project_owner.id)
    group = Group(id=1, project=project, in_charge_user_id=group_owner.id)
    storage_usage = StorageUsage(id=1, group=group)

    assert group_capabilities(group_owner, group) == {"adjust_quota": False}
    assert group_capabilities(project_owner, group) == {"adjust_quota": False}
    assert group_capabilities(super_admin, group) == {"adjust_quota": True}
    assert storage_usage_capabilities(project_owner, storage_usage) == {"adjust_quota": True}
    assert storage_usage_capabilities(group_owner, storage_usage) == {"adjust_quota": False}
    assert storage_usage_capabilities(super_admin, storage_usage) == {"adjust_quota": True}
