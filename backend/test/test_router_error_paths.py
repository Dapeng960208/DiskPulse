# -*- coding: utf-8 -*-
from datetime import datetime

import pytest
from fastapi import HTTPException, BackgroundTasks

from routers import aggregate, projects, qtrees, storage_usage, volumes
from schemas.aggregateSchema import AggregateUpdate
from schemas.projectsSchema import ProjectUpdate
from schemas.qtreeSchema import QtreeUpdate
from schemas.storageUsageSchema import BackUp, StorageUsageUpdate
from schemas.volumeSchema import VolumeUpdate


NOW = datetime(2026, 7, 15, 10, 0)


def assert_not_found(call, detail):
    with pytest.raises(HTTPException) as error:
        call()
    assert error.value.status_code == 404
    assert error.value.detail == detail


def test_aggregate_router_error_paths(db_session):
    update = AggregateUpdate(
        name="aggregate",
        limit=100,
        used=10,
        use_ratio=10,
        updated_at=NOW,
    )
    assert_not_found(lambda: aggregate.read_aggregate(404, db_session), "Aggregate not found")
    assert_not_found(
        lambda: aggregate.read_aggregate_realtime_data(404, db=db_session),
        "Aggregate not found",
    )
    assert_not_found(
        lambda: aggregate.update_aggregate(404, update, db=db_session),
        "Aggregate not found",
    )
    assert_not_found(lambda: aggregate.delete_aggregate(404, db=db_session), "Aggregate not found")
    assert_not_found(
        lambda: aggregate.get_aggregate_storage_tree_by_id(404, db=db_session),
        "Aggregate not found",
    )


def test_volume_and_qtree_router_error_paths(db_session):
    volume_update = VolumeUpdate(
        name="volume",
        vserver="svm",
        aggregate="aggregate",
        type="rw",
        state="online",
        updated_at=NOW,
    )
    assert_not_found(lambda: volumes.read_volume(404, db_session), "Volume not found")
    assert_not_found(
        lambda: volumes.read_volume_realtime_data(404, db=db_session),
        "Volume not found",
    )
    assert_not_found(
        lambda: volumes.update_volume(404, volume_update, db=db_session),
        "Volume not found",
    )
    assert_not_found(lambda: volumes.delete_volume(404, db=db_session), "Volume not found")

    qtree_update = QtreeUpdate(
        volume_id=1,
        name="qtree",
        style="unix",
        oplocks="enabled",
        status="normal",
        updated_at=NOW,
    )
    assert_not_found(lambda: qtrees.read_qtree(404, db_session), "Qtree not found")
    assert_not_found(
        lambda: qtrees.read_qtree_realtime_data(404, db=db_session),
        "Qtree not found",
    )
    assert_not_found(
        lambda: qtrees.update_qtree(404, qtree_update, db=db_session),
        "Qtree not found",
    )
    assert_not_found(lambda: qtrees.delete_qtree(404, db=db_session), "Qtree not found")


def test_project_and_storage_usage_router_error_paths(db_session):
    assert projects.read_projects(prop=None, order=None, db=db_session).total == 0
    assert projects.get_project_storage_summary(db=db_session).data == [["project"]]
    assert projects.get_project_groups_storage_usage(db=db_session).data == {}
    assert projects.get_project_storage_tree_by_id(404, db=db_session).data == []

    project_update = ProjectUpdate(name="project")
    assert_not_found(
        lambda: projects.read_project_storage_usage_by_id(404, db=db_session),
        "The project was not found",
    )
    assert_not_found(
        lambda: projects.read_project_by_id(404, db=db_session),
        "The project was not found",
    )
    assert_not_found(
        lambda: projects.update_project_by_id(404, project_update, db=db_session),
        "The project was not found",
    )

    assert_not_found(
        lambda: storage_usage.read_storage_usage(404, db=db_session),
        "StorageUsage not found",
    )
    assert_not_found(
        lambda: storage_usage.read_storage_usage_realtime_data(404, db=db_session),
        "StorageUsage not found",
    )
    assert_not_found(
        lambda: storage_usage.update_storage_usage(
            404,
            StorageUsageUpdate(user_id=1, group_id=1),
            db=db_session,
        ),
        "StorageUsage not found",
    )
    assert_not_found(
        lambda: storage_usage.delete_storage_usage(404, db=db_session),
        "StorageUsage not found",
    )
    response = storage_usage.back_up_storage_usage(
        404,
        BackgroundTasks(),
        BackUp(closed=False),
        db=db_session,
    )
    assert response.status_code == 200
    with pytest.raises(HTTPException, match="No export type"):
        storage_usage.export_storage_usages(export_type="csv", db=db_session)
