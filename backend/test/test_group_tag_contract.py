# -*- coding: utf-8 -*-
from typing import get_args

import pytest
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from appConfig import base_config
from main import app
import models
from routers import group, group_tag
from schemas import groupSchema, groupTagSchema
from utils.security import issue_token


API_PREFIX = "/storage-pulse/api"
GROUP_TAGS = f"{API_PREFIX}/group-tags"


def _foreign_keys(table) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    return {
        constraint.name: (
            tuple(column.name for column in constraint.columns),
            tuple(element.target_fullname for element in constraint.elements),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def test_group_tag_is_a_name_only_lookup():
    table = models.GroupTag.__table__

    assert set(table.c.keys()) == {"id", "name"}
    assert table.c.name.nullable is False
    assert table.c.name.type.length == 128
    assert {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }["uq_group_tag_name"] == ("name",)

    assert set(groupTagSchema.GroupTag.model_fields) == {
        "id",
        "name",
    }


def test_group_owns_project_cluster_and_tag_relations():
    table = models.Group.__table__
    assert {"project_id", "storage_cluster_id", "group_tag_id"} <= set(
        table.c.keys()
    )
    assert all(
        table.c[field].nullable is False
        for field in ("project_id", "storage_cluster_id", "group_tag_id")
    )
    foreign_keys = _foreign_keys(table)
    assert foreign_keys["fk_group_project"] == (("project_id",), ("projects.id",))
    assert foreign_keys["fk_group_storage_cluster"] == (
        ("storage_cluster_id",),
        ("storage_clusters.id",),
    )
    assert foreign_keys["fk_group_tag"] == (
        ("group_tag_id",),
        ("group_tags.id",),
    )

    for field_name in ("project_id", "storage_cluster_id", "group_tag_id"):
        field = groupSchema.GroupBindingCreate.model_fields[field_name]
        assert field.is_required()
        assert type(None) not in get_args(field.annotation)


def test_group_tag_routes_are_global_crud():
    routes = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    assert {
        ("GET", GROUP_TAGS),
        ("POST", GROUP_TAGS),
        ("GET", f"{GROUP_TAGS}/{{group_tag_id}}"),
        ("PUT", f"{GROUP_TAGS}/{{group_tag_id}}"),
        ("DELETE", f"{GROUP_TAGS}/{{group_tag_id}}"),
    } <= routes
    assert not any(
        "storage-environments" in path
        for _method, path in routes
    )


@pytest.fixture
def tag_api(api_client_factory, session_factory):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        session.add_all(
            [
                models.User(id=1, rd_username="admin", username="Admin"),
                models.Project(id=1, name="project-1"),
                models.StorageCluster(
                    id=1,
                    name="cluster-1",
                    storage_type="netapp",
                    storage_host="storage.internal",
                    storage_user="collector",
                    storage_password="secret",
                ),
                models.GroupTag(id=1, name="production"),
                models.Volume(id=1, storage_cluster_id=1, name="volume-1"),
            ]
        )
        session.flush()
        session.add_all(
            [
                models.Qtree(
                    id=1,
                    storage_cluster_id=1,
                    volume_id=1,
                    name="qtree-1",
                ),
                models.Group(
                id=1,
                name="group-1",
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                ),
                models.Group(
                    id=99,
                    name="qtree-group",
                    project_id=1,
                    storage_cluster_id=1,
                    group_tag_id=1,
                    qtree_id=1,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    return api_client_factory(
        [group_tag.router, group.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )


def test_group_tag_crud_accepts_only_name(tag_api):
    listed = tag_api.get(GROUP_TAGS, params={"page": 1, "size": 20})
    assert listed.status_code == 200
    assert listed.json() == {"content": [{"id": 1, "name": "production"}], "total": 1}

    created = tag_api.post(GROUP_TAGS, json={"name": "  disaster-recovery  "})
    assert created.status_code == 201
    assert created.json()["name"] == "disaster-recovery"
    assert set(created.json()) == {"id", "name"}

    rejected = tag_api.post(
        GROUP_TAGS,
        json={"name": "invalid", "project_id": 1, "storage_cluster_id": 1},
    )
    assert rejected.status_code == 422


def test_group_create_uses_direct_relations_and_group_tag(tag_api):
    response = tag_api.post(
        f"{API_PREFIX}/groups/",
        json={
            "name": "group-2",
            "project_id": 1,
            "storage_cluster_id": 1,
            "group_tag_id": 1,
            "volume_id": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"] == {
        "id": 1,
        "name": "project-1",
        "limit": 0.0,
        "soft_limit": None,
        "used": 0.0,
        "use_ratio": 0.0,
        "soft_use_ratio": None,
        "is_common": False,
        "status": 1,
        "project_process_code": None,
        "capacity": {
            "limit": {"value": 0, "unit": "MB"},
            "used": {"value": 0, "unit": "MB"},
        },
    }
    assert payload["storage_cluster"] == {
        "id": 1,
        "name": "cluster-1",
        "storage_type": "netapp",
    }
    assert payload["group_tag"] == {"id": 1, "name": "production"}


def test_linked_group_tag_cannot_be_deleted(tag_api):
    response = tag_api.delete(f"{GROUP_TAGS}/1")

    assert response.status_code == 409
    assert "group" in response.text.lower()


def test_group_list_filters_by_volume_id(tag_api):
    response = tag_api.get(f"{API_PREFIX}/groups/", params={"volume_id": 1})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["content"]] == [1]


def test_group_list_rejects_volume_and_qtree_filters_together(tag_api):
    response = tag_api.get(
        f"{API_PREFIX}/groups/",
        params={"volume_id": 1, "qtree_id": 1},
    )

    assert response.status_code == 422
