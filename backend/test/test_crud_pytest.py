# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import models
from crud import aggregateCrud, groupCrud, projectsCrud, qtreeCrud, usersCrud, volumeCrud
from schemas import aggregateSchema, groupSchema, projectsSchema, qtreeSchema, usersSchema, volumeSchema
from utils.query import get_sort_column, require_allowed


NOW = datetime(2026, 6, 30, 10, 0, 0)


def seed_storage_tree(db_session):
    user = models.User(
        id=1,
        username="Alice Zhang",
        rd_username="alice",
        email="alice@example.com",
        user_type=2,
        storage_used=30,
        updated_at=NOW,
    )
    second_user = models.User(
        id=2,
        username="Bob Li",
        rd_username="bob",
        email="bob@example.com",
        user_type=1,
        storage_used=10,
        updated_at=NOW,
    )
    project = models.Project(
        id=1,
        name="alpha",
        recipients="1 2",
        is_alert=True,
        is_common=False,
        status=1,
        limit=2048,
        soft_limit=1536,
        used=1024,
        use_ratio=50,
        soft_use_ratio=66.67,
        updated_at=NOW,
    )
    common_project = models.Project(id=2, name="Common", is_common=True, status=1, limit=1024, used=256)
    cluster = models.StorageCluster(
        id=1,
        name="cluster-a",
        storage_type="netapp",
        storage_host="storage.local",
        storage_port=443,
        is_active=True,
        limit=4096,
        used=2048,
        use_ratio=50,
    )
    group_tag = models.GroupTag(id=1, name="production")
    aggregate = models.Aggregate(
        id=1,
        storage_cluster_id=1,
        name="aggr-a",
        limit=4096,
        used=2048,
        use_ratio=50,
        updated_at=NOW,
    )
    volume = models.Volume(
        id=1,
        storage_cluster_id=1,
        name="vol-a",
        vserver="svm-a",
        aggregate="aggr-a",
        type="rw",
        state="online",
        limit=2048,
        soft_limit=1536,
        used=1024,
        use_ratio=50,
        soft_use_ratio=66.67,
        allocated=1200,
        updated_at=NOW,
    )
    qtree = models.Qtree(
        id=1,
        storage_cluster_id=1,
        volume_id=1,
        name="qtree-a",
        limit=1024,
        soft_limit=768,
        used=512,
        use_ratio=50,
        soft_use_ratio=66.67,
        style="unix",
        oplocks="enabled",
        status="normal",
        updated_at=NOW,
    )
    group = models.Group(
        id=1,
        project_id=1,
        storage_cluster_id=1,
        group_tag_id=1,
        qtree_id=1,
        name="alpha-team",
        linux_path="/data/alpha",
        limit=1024,
        soft_limit=768,
        used=512,
        use_ratio=50,
        soft_use_ratio=66.67,
        enable_monitoring=True,
        updated_at=NOW,
    )
    storage_usage = models.StorageUsage(
        id=1,
        storage_cluster_id=1,
        user_id=1,
        group_id=1,
        linux_path="/data/alpha/alice",
        limit=256,
        soft_limit=192,
        used=128,
        use_ratio=50,
        soft_use_ratio=66.67,
        file_used=12,
        file_limit=1000,
        updated_at=NOW,
    )
    db_session.add_all(
        [
            user,
            second_user,
            project,
            common_project,
            cluster,
            group_tag,
            aggregate,
            volume,
            qtree,
            group,
            storage_usage,
        ]
    )
    db_session.commit()


def test_project_crud_lists_and_storage_summaries(db_session):
    seed_storage_tree(db_session)

    created = projectsCrud.create_project(
        db_session,
        projectsSchema.ProjectUpdate(
            name="beta",
            descriptions="new project",
            status=2,
            is_common=False,
            project_process_code="P-2",
            recipient_ids=[1, 2],
            is_alert=True,
            in_charge_user_id=1,
        ),
    )
    assert created.recipients == "1 2"

    updated = projectsCrud.update_project(
        db_session,
        created.id,
        projectsSchema.ProjectUpdate(
            name="beta-renamed",
            descriptions="updated",
            status=1,
            is_common=True,
            project_process_code="P-3",
            recipient_ids=[2],
            is_alert=False,
            in_charge_user_id=2,
        ),
    )
    assert updated.name == "beta-renamed"
    assert updated.recipients == "2"

    projects, total = projectsCrud.get_projects(
        db_session,
        page=1,
        size=10,
        nameLike="alpha",
        prop="used",
        order="descending",
        status=1,
    )
    assert total == 1
    assert projects[0].name == "alpha"
    assert projectsCrud.get_project_by_name(db_session, "alpha").id == 1
    assert projectsCrud.get_project_by_id(db_session, 1).name == "alpha"
    assert projectsCrud.get_common_project(db_session).name == "Common"

    storage_summary = projectsCrud.get_project_storage_summary(db_session)
    assert storage_summary == [["project", "alpha"], ["alpha-team", 0.5]]

    tree = projectsCrud.get_project_tree_summary(db_session)
    assert tree[0]["name"] == "alpha"
    assert tree[0]["children"][0]["children"][0]["name"] == "alice"

    project_tree = projectsCrud.get_project_tree_summary_by_id(db_session, 1, "soft_limit")
    assert project_tree[0]["name"] == "alpha-team"
    assert project_tree[0]["children"][0]["value"] == 0.19

    with pytest.raises(HTTPException):
        projectsCrud.get_project_tree_summary_by_id(db_session, 1, "bad_value")


def test_user_crud_search_sort_update_and_delete(db_session):
    seed_storage_tree(db_session)

    created = usersCrud.create_user(
        db_session,
        usersSchema.UserBase(
            username="Carol Chen",
            rd_username="carol",
            email="carol@example.com",
            user_type=2,
            is_alert=True,
        ),
    )
    assert usersCrud.get_user_by_rd_username(db_session, "carol").id == created.id
    assert usersCrud.get_user_by_rd_username(db_session, None) is None
    assert usersCrud.get_user_by_id(db_session, created.id).rd_username == "carol"

    users, total = asyncio.run(
        usersCrud.get_users(
            db_session,
            page=1,
            size=10,
            nameLike="alice",
            prop="storage_used",
            order="descending",
            user_type=2,
        )
    )
    assert total == 1
    assert users[0].rd_username == "alice"

    updated = usersCrud.update_user(
        db_session,
        created.id,
        usersSchema.UserUpdate(username="Carol Updated", email="new@example.com", user_type=1, is_alert=False),
    )
    assert updated.username == "Carol Updated"
    assert updated.is_alert is False
    assert usersCrud.update_user(db_session, 9999, usersSchema.UserUpdate(username="missing")) is None

    usersCrud.delete_user_by_id(db_session, 1)
    assert usersCrud.get_user_by_id(db_session, 1) is None
    assert db_session.query(models.StorageUsage).filter_by(user_id=1).count() == 0


def test_storage_resource_crud_filters_tree_and_realtime_helpers(db_session):
    seed_storage_tree(db_session)

    aggregates, aggregate_total = aggregateCrud.get_aggregates(
        db_session,
        page=1,
        size=10,
        nameLike="aggr",
        prop="used",
        order="descending",
        storage_cluster_id=1,
    )
    assert aggregate_total == 1
    assert aggregates[0].name == "aggr-a"

    created_aggregate = aggregateCrud.create_aggregate(
        db_session,
        aggregateSchema.AggregateCreate(
            name="aggr-b",
            limit=100,
            used=10,
            use_ratio=10,
            updated_at=NOW,
            storage_cluster_id=1,
        ),
    )
    updated_aggregate = aggregateCrud.update_aggregate(
        db_session,
        created_aggregate.id,
        aggregateSchema.AggregateUpdate(
            name="aggr-c",
            limit=200,
            used=20,
            use_ratio=10,
            updated_at=NOW,
            storage_cluster_id=1,
        ),
    )
    assert updated_aggregate.name == "aggr-c"
    assert aggregateCrud.get_aggregate_by_id(db_session, created_aggregate.id).name == "aggr-c"
    assert aggregateCrud.delete_aggregate(db_session, created_aggregate.id).name == "aggr-c"

    aggregate_tree = aggregateCrud.get_aggregate_tree_summary_by_name(db_session, "aggr-a", "used")
    assert aggregate_tree[0]["children"][0]["name"] == "qtree-a"
    assert aggregateCrud.get_aggregate_tree_summary(db_session, "used")[0]["name"] == "vol-a"
    with pytest.raises(HTTPException):
        aggregateCrud.get_aggregate_tree_summary(db_session, "unsafe")

    volumes, volume_total = volumeCrud.get_volumes(
        db_session,
        page=1,
        size=10,
        nameLike="svm",
        prop="soft_limit",
        order="ascending",
        storage_cluster_id=1,
    )
    assert volume_total == 1
    assert volumes[0].name == "vol-a"

    created_volume = volumeCrud.create_volume(
        db_session,
        volumeSchema.VolumeCreate(
            name="vol-b",
            vserver="svm-b",
            aggregate="aggr-a",
            type="rw",
            state="online",
            limit=100,
            soft_limit=80,
            used=20,
            use_ratio=20,
            soft_use_ratio=25,
            allocated=30,
            updated_at=NOW,
            storage_cluster_id=1,
        ),
    )
    updated_volume = volumeCrud.update_volume(
        db_session,
        created_volume.id,
        volumeSchema.VolumeUpdate(
            name="vol-c",
            vserver="svm-b",
            aggregate="aggr-a",
            type="rw",
            state="offline",
            limit=100,
            soft_limit=80,
            used=20,
            use_ratio=20,
            soft_use_ratio=25,
            allocated=30,
            updated_at=NOW,
            storage_cluster_id=1,
        ),
    )
    assert updated_volume.state == "offline"
    assert volumeCrud.get_volume_by_id(db_session, created_volume.id).name == "vol-c"
    assert volumeCrud.delete_volume(db_session, created_volume.id).name == "vol-c"

    qtrees, qtree_total = qtreeCrud.get_qtrees(
        db_session,
        page=1,
        size=10,
        nameLike="vol-a",
        prop="soft_use_ratio",
        order="descending",
        volume_id=1,
        storage_cluster_id=1,
    )
    assert qtree_total == 1
    assert qtrees[0].name == "qtree-a"

    created_qtree = qtreeCrud.create_qtree(
        db_session,
        qtreeSchema.QtreeCreate(
            volume_id=1,
            name="qtree-b",
            limit=100,
            soft_limit=80,
            used=20,
            use_ratio=20,
            soft_use_ratio=25,
            style="unix",
            oplocks="enabled",
            status="normal",
            updated_at=NOW,
            storage_cluster_id=1,
        ),
    )
    updated_qtree = qtreeCrud.update_qtree(
        db_session,
        created_qtree.id,
        qtreeSchema.QtreeUpdate(
            volume_id=1,
            name="qtree-c",
            limit=100,
            soft_limit=80,
            used=20,
            use_ratio=20,
            soft_use_ratio=25,
            style="unix",
            oplocks="disabled",
            status="normal",
            updated_at=NOW,
            storage_cluster_id=1,
        ),
    )
    assert updated_qtree.oplocks == "disabled"
    assert qtreeCrud.get_qtree_by_id(db_session, created_qtree.id).name == "qtree-c"
    assert qtreeCrud.delete_qtree(db_session, created_qtree.id).name == "qtree-c"

    with patch("crud.aggregateCrud.get_real_time_data_by_id", return_value=[["t", 1]]) as aggregate_realtime:
        assert aggregateCrud.get_aggregate_real_time_data_by_id(db_session, 1) == [["t", 1]]
    aggregate_realtime.assert_called_once()

    with patch("crud.volumeCrud.get_real_time_data_by_id", return_value=[["t", 2]]) as volume_realtime:
        assert volumeCrud.get_volume_real_time_data_by_id(db_session, 1) == [["t", 2]]
    volume_realtime.assert_called_once()

    with patch("crud.qtreeCrud.get_real_time_data_by_id", return_value=[["t", 3]]) as qtree_realtime:
        assert qtreeCrud.get_qtree_real_time_data_by_id(db_session, 1) == [["t", 3]]
    qtree_realtime.assert_called_once()


def test_group_crud_filters_realtime_and_cascades_storage_usages(db_session):
    seed_storage_tree(db_session)

    groups, total = groupCrud.get_groups(
        db_session,
        page=1,
        size=10,
        nameLike="alpha",
        prop="soft_limit",
        order="descending",
        qtree_id=1,
        project_id=1,
        storage_cluster_id=1,
    )
    assert total == 1
    assert groups[0].name == "alpha-team"

    created = groupCrud.create_group(
        db_session,
        groupSchema.GroupBindingCreate(
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            qtree_id=1,
            name="beta-team",
            linux_path="/data/beta",
            limit=100,
            soft_limit=80,
            used=20,
            use_ratio=20,
            soft_use_ratio=25,
            updated_at=NOW,
        ),
    )
    updated = groupCrud.update_group(
        db_session,
        created.id,
        groupSchema.GroupBindingUpdate(
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            qtree_id=1,
            name="beta-renamed",
            linux_path="/data/beta",
            limit=200,
            soft_limit=160,
            used=40,
            use_ratio=20,
            soft_use_ratio=25,
            updated_at=NOW,
        ),
    )
    assert updated.name == "beta-renamed"
    assert groupCrud.get_group_by_id(db_session, created.id).limit == 200

    with patch("crud.groupCrud.get_real_time_data_by_id", return_value=[["t", 4]]) as group_realtime:
        assert groupCrud.get_group_real_time_data_by_id(db_session, 1) == [["t", 4]]
    group_realtime.assert_called_once()

    groupCrud.delete_group(db_session, 1)
    assert groupCrud.get_group_by_id(db_session, 1) is None
    assert db_session.query(models.StorageUsage).filter_by(group_id=1).count() == 0


def test_query_helpers_reject_unsafe_fields():
    assert get_sort_column(models.User, "storage_used") is models.User.storage_used
    assert get_sort_column(models.User, None) is None

    with pytest.raises(HTTPException):
        get_sort_column(models.User, "_sa_instance_state")

    with pytest.raises(HTTPException):
        get_sort_column(models.User, "does_not_exist")

    assert require_allowed("used", {"used", "limit"}, "value_type") == "used"
    with pytest.raises(HTTPException):
        require_allowed("bad", {"used", "limit"}, "value_type")
