# -*- coding: utf-8 -*-
from datetime import datetime
import importlib.util
import io
from pathlib import Path
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException

import models
from appConfig import base_config
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from routers import project_memberships
from schemas import projectsSchema, storageUsageSchema
from services import project_access_service, project_membership_service


def _membership_migration():
    path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000009_project_rbac_unified_audit.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _seed_project_users(db):
    db.add_all(
        [
            models.User(id=1, rd_username="super-admin", username="Super Admin"),
            models.User(id=2, rd_username="owner", username="Project Owner"),
            models.User(id=3, rd_username="editor", username="Project Editor"),
            models.User(id=4, rd_username="reader", username="Project Reader"),
        ]
    )
    db.flush()
    project = models.Project(id=1, name="project-a", in_charge_user_id=2)
    db.add(project)
    db.commit()
    return project


def test_project_owner_is_initialized_as_project_admin_and_pt_user_is_absent(db_session):
    _seed_project_users(db_session)

    project_access_service.ensure_project_owner_membership(db_session, project_id=1)
    db_session.commit()

    membership = db_session.query(models.ProjectMembership).filter_by(project_id=1, user_id=2).one()
    assert membership.role == "project_admin"
    assert "pt_user_id" not in projectsSchema.ProjectUpdate.model_fields
    assert not hasattr(models.Project, "pt_user_id")


def test_project_membership_migration_compiles_for_supported_dialects():
    for dialect_name in ("sqlite", "postgresql", "mysql"):
        migration = _membership_migration()
        output = io.StringIO()
        migration.op = Operations(
            MigrationContext.configure(
                dialect_name=dialect_name,
                opts={"as_sql": True, "output_buffer": output},
            )
        )
        migration.upgrade()
        migration.downgrade()
        sql = output.getvalue().lower()
        assert "project_memberships" in sql
        assert "pt_user_id" in sql


def test_project_membership_migration_backfills_owner_and_drops_pt_user_on_sqlite(
    monkeypatch,
    tmp_path,
):
    database_url = f"sqlite:///{(tmp_path / 'project-rbac.sqlite').as_posix()}"
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)

    command.upgrade(alembic_config, "000000000007")
    engine = sa.create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("INSERT INTO users (id) VALUES (:id)"),
                [{"id": 1}, {"id": 2}],
            )
            connection.execute(
                sa.text(
                    "INSERT INTO projects "
                    "(id, name, in_charge_user_id, pt_user_id) "
                    "VALUES (:id, :name, :owner_id, :pt_user_id)"
                ),
                {
                    "id": 1,
                    "name": "project-a",
                    "owner_id": 1,
                    "pt_user_id": 2,
                },
            )

        command.upgrade(alembic_config, "000000000009")
        with engine.connect() as connection:
            membership = connection.execute(
                sa.text("SELECT project_id, user_id, role FROM project_memberships")
            ).one()
            assert membership == (1, 1, "project_admin")
            assert "pt_user_id" not in {
                column["name"]
                for column in sa.inspect(connection).get_columns("projects")
            }

        command.downgrade(alembic_config, "000000000007")
        with engine.connect() as connection:
            assert "pt_user_id" in {
                column["name"]
                for column in sa.inspect(connection).get_columns("projects")
            }
            assert "project_memberships" not in sa.inspect(connection).get_table_names()
    finally:
        engine.dispose()


def test_project_admin_can_manage_reader_and_editor_but_not_project_admin(db_session):
    _seed_project_users(db_session)
    project_access_service.ensure_project_owner_membership(db_session, project_id=1)
    db_session.commit()

    created = project_membership_service.create_membership(
        db_session,
        project_id=1,
        user_id=3,
        role="editor",
        current_user=db_session.get(models.User, 2),
    )

    assert created["role"] == "editor"
    with pytest.raises(HTTPException) as error:
        project_membership_service.create_membership(
            db_session,
            project_id=1,
            user_id=4,
            role="project_admin",
            current_user=db_session.get(models.User, 2),
        )
    assert error.value.status_code == 403


def test_membership_api_enforces_local_user_and_project_admin_role_boundary(
    api_client_factory,
    session_factory,
):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["super-admin"])
    session = session_factory()
    try:
        _seed_project_users(session)
    finally:
        session.close()
    client = api_client_factory(
        [project_memberships.router],
        headers={"Authorization": "Bearer invalid-placeholder"},
    )
    from utils.security import issue_token

    client.headers.update({"Authorization": f"Bearer {issue_token(1)}"})
    created = client.post(
        "/storage-pulse/api/projects/1/members",
        json={"user_id": 3, "role": "project_admin"},
    )
    assert created.status_code == 201
    assert created.json()["role"] == "project_admin"

    session = session_factory()
    try:
        owner = session.get(models.User, 2)
        project_access_service.ensure_project_owner_membership(session, project_id=1)
        session.commit()
        owner_token = issue_token(owner.id)
    finally:
        session.close()
    client.headers.update({"Authorization": f"Bearer {owner_token}"})
    denied = client.post(
        "/storage-pulse/api/projects/1/members",
        json={"user_id": 4, "role": "project_admin"},
    )
    missing_user = client.post(
        "/storage-pulse/api/projects/1/members",
        json={"user_id": 99, "role": "reader"},
    )
    assert denied.status_code == 403
    assert missing_user.status_code == 404


def test_storage_collection_grants_reader_without_downgrading_existing_membership(db_session):
    db_session.add_all(
        [
            models.User(id=1, rd_username="alice", username="Alice"),
            models.Project(id=1, name="project-a"),
            models.StorageCluster(id=1, name="cluster-a", storage_type="netapp", is_active=True),
            models.GroupTag(id=1, name="production"),
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                name="group-a",
                linux_path="/data/project-a",
                enable_monitoring=False,
            ),
        ]
    )
    db_session.commit()
    monitor = StoragePulseMonitor(
        db_session,
        logger=Mock(),
        storage_cluster_id=1,
        snapshot={"storage_type": "netapp", "storage_cluster_name": "cluster-a"},
    )
    item = storageUsageSchema.StorageUsageBase(
        storage_cluster_id=1,
        user_id=1,
        group_id=1,
        linux_path="/data/project-a/alice",
        limit=10,
        used=2,
        updated_at=datetime.now(),
    )

    monitor.sync_data_to_postgres(
        [item],
        models.StorageUsage,
        ["group_id", "user_id", "storage_cluster_id"],
        exclude_keys=["group_id", "user_id", "storage_cluster_id"],
    )
    db_session.commit()
    assert db_session.query(models.ProjectMembership).filter_by(project_id=1, user_id=1).one().role == "reader"

    project_access_service.set_project_member(
        db_session,
        project_id=1,
        user_id=1,
        role="editor",
        actor_is_super_admin=True,
    )
    monitor.sync_data_to_postgres(
        [item],
        models.StorageUsage,
        ["group_id", "user_id", "storage_cluster_id"],
        exclude_keys=["group_id", "user_id", "storage_cluster_id"],
    )
    db_session.commit()

    assert db_session.query(models.ProjectMembership).filter_by(project_id=1, user_id=1).one().role == "editor"


def test_existing_directory_users_are_added_as_readers_without_downgrading_roles(db_session):
    db_session.add_all(
        [
            models.User(id=11, rd_username="reader", username="Reader"),
            models.User(id=12, rd_username="editor", username="Editor"),
            models.Project(id=11, name="project-directory-members"),
            models.StorageCluster(id=11, name="cluster-directory-members", storage_type="netapp", is_active=True),
            models.GroupTag(id=11, name="directory-members"),
            models.Group(
                id=11,
                project_id=11,
                storage_cluster_id=11,
                group_tag_id=11,
                name="group-directory-members",
                linux_path="/data/project-directory-members",
                enable_monitoring=False,
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            models.StorageUsage(user_id=11, group_id=11, linux_path="/data/project-directory-members/reader", updated_at=datetime.now()),
            models.StorageUsage(user_id=12, group_id=11, linux_path="/data/project-directory-members/editor", updated_at=datetime.now()),
            models.ProjectMembership(project_id=11, user_id=12, role="editor"),
        ]
    )
    db_session.commit()

    project_access_service.ensure_group_directory_readers(db_session, group_id=11)
    db_session.commit()

    memberships = {
        membership.user_id: membership.role
        for membership in db_session.query(models.ProjectMembership)
        .filter_by(project_id=11)
        .all()
    }
    assert memberships == {11: "reader", 12: "editor"}


def test_directory_owner_membership_cannot_be_removed_while_directory_exists(db_session):
    base_config.set("super_admin_usernames", ["super-admin"])
    admin = models.User(id=21, rd_username="super-admin", username="Admin")
    owner = models.User(id=22, rd_username="owner", username="Owner")
    project = models.Project(id=21, name="protected-directory-project")
    cluster = models.StorageCluster(id=21, name="protected-directory-cluster", storage_type="netapp", is_active=True)
    tag = models.GroupTag(id=21, name="protected-directory-tag")
    group = models.Group(
        id=21,
        project_id=21,
        storage_cluster_id=21,
        group_tag_id=21,
        name="protected-directory-group",
        linux_path="/data/protected-directory",
        enable_monitoring=False,
    )
    db_session.add_all([admin, owner, project, cluster, tag, group])
    db_session.flush()
    db_session.add_all(
        [
            models.StorageUsage(user_id=22, group_id=21, linux_path="/data/protected-directory/owner", updated_at=datetime.now()),
            models.ProjectMembership(project_id=21, user_id=22, role="reader"),
        ]
    )
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        project_membership_service.delete_membership(
            db_session,
            project_id=21,
            user_id=22,
            current_user=admin,
        )

    assert error.value.status_code == 409
    assert db_session.query(models.ProjectMembership).filter_by(project_id=21, user_id=22).one()
