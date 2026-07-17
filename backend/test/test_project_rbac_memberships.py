# -*- coding: utf-8 -*-
from datetime import datetime

import pytest
from fastapi import HTTPException

import models
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from schemas import projectsSchema, storageUsageSchema
from services import project_access_service, project_membership_service


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

    assert created.role == "editor"
    with pytest.raises(HTTPException) as error:
        project_membership_service.create_membership(
            db_session,
            project_id=1,
            user_id=4,
            role="project_admin",
            current_user=db_session.get(models.User, 2),
        )
    assert error.value.status_code == 403


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
            ),
        ]
    )
    db_session.commit()
    monitor = StoragePulseMonitor(
        db_session,
        logger=object(),
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

    project_membership_service.update_membership(
        db_session,
        project_id=1,
        user_id=1,
        role="editor",
        current_user=models.User(id=99, rd_username="super-admin"),
        is_super_admin_override=True,
    )
    monitor.sync_data_to_postgres(
        [item],
        models.StorageUsage,
        ["group_id", "user_id", "storage_cluster_id"],
        exclude_keys=["group_id", "user_id", "storage_cluster_id"],
    )
    db_session.commit()

    assert db_session.query(models.ProjectMembership).filter_by(project_id=1, user_id=1).one().role == "editor"
