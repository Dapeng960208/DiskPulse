# -*- coding: utf-8 -*-
from datetime import datetime
from typing import get_args

import pytest
from sqlalchemy import event

from appConfig import base_config
import models
from routers import group, qtrees, storage_cluster, volumes
from schemas import groupSchema
from utils.security import issue_token


API_PREFIX = "/storage-pulse/api"
NOW = datetime.fromisoformat("2026-07-13T10:00:00")


def _bound_group(*, project_id: int, storage_cluster_id: int, **values):
    record = models.Group(**values)
    if hasattr(models.Group, "project_id"):
        record.project_id = project_id
    if hasattr(models.Group, "storage_cluster_id"):
        record.storage_cluster_id = storage_cluster_id
    return record


def test_group_response_requires_environment_binding_contract():
    for field_name in ("project_environment_id", "project_environment"):
        field = groupSchema.Group.model_fields[field_name]
        assert field.is_required()
        assert type(None) not in get_args(field.annotation)


@pytest.fixture
def binding_api(api_client_factory, session_factory):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        session.add(models.User(id=1, rd_username="admin", username="Admin"))
        session.add_all(
            [
                models.Project(id=1, name="project-1"),
                models.Project(id=2, name="project-2"),
                models.StorageCluster(
                    id=1,
                    name="netapp-1",
                    storage_type="netapp",
                    storage_host="netapp.internal",
                    storage_user="collector",
                    storage_password="secret",
                ),
                models.StorageCluster(
                    id=2,
                    name="isilon-1",
                    storage_type="isilon",
                    storage_host="isilon.internal",
                    storage_user="collector",
                    storage_password="secret",
                ),
                models.StorageCluster(
                    id=3,
                    name="netapp-2",
                    storage_type="netapp",
                    storage_host="netapp-2.internal",
                    storage_user="collector",
                    storage_password="secret",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                models.ProjectStorageEnvironment(
                    id=1,
                    project_id=1,
                    storage_cluster_id=1,
                    name="environment-1",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.ProjectStorageEnvironment(
                    id=2,
                    project_id=1,
                    storage_cluster_id=2,
                    name="environment-2",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.ProjectStorageEnvironment(
                    id=3,
                    project_id=2,
                    storage_cluster_id=3,
                    name="environment-3",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.Volume(id=1, storage_cluster_id=1, name="volume-1"),
                models.Volume(id=2, storage_cluster_id=2, name="volume-2"),
                models.Volume(id=3, storage_cluster_id=3, name="volume-3"),
                models.Volume(id=4, storage_cluster_id=3, name="volume-4"),
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
                models.Qtree(
                    id=2,
                    storage_cluster_id=2,
                    volume_id=2,
                    name="qtree-2",
                ),
                models.Qtree(
                    id=3,
                    storage_cluster_id=3,
                    volume_id=3,
                    name="qtree-3",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                _bound_group(
                    id=1,
                    name="volume-group",
                    project_environment_id=1,
                    volume_id=1,
                    project_id=1,
                    storage_cluster_id=1,
                ),
                _bound_group(
                    id=2,
                    name="qtree-group",
                    project_environment_id=1,
                    qtree_id=1,
                    project_id=1,
                    storage_cluster_id=1,
                ),
                _bound_group(
                    id=3,
                    name="other-environment-group",
                    project_environment_id=2,
                    volume_id=2,
                    project_id=1,
                    storage_cluster_id=2,
                ),
                _bound_group(
                    id=4,
                    name="protected-volume-group",
                    project_environment_id=3,
                    volume_id=4,
                    project_id=2,
                    storage_cluster_id=3,
                ),
                models.Group(
                    id=5,
                    name="environment-derived-filter-group",
                    project_environment_id=3,
                    volume_id=3,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    return api_client_factory(
        [group.router, storage_cluster.router, volumes.router, qtrees.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"project_environment_id": 1, "volume_id": 1, "qtree_id": 1},
        {"project_environment_id": 1},
        {"project_environment_id": 2, "qtree_id": 2},
        {"project_environment_id": 1, "volume_id": 3},
    ],
    ids=("both-targets", "missing-target", "isilon-qtree", "target-wrong-cluster"),
)
def test_group_create_and_update_validate_environment_target_pair(binding_api, payload):
    create_response = binding_api.post(
        f"{API_PREFIX}/groups/",
        json={"name": "invalid-binding", **payload},
    )
    update_response = binding_api.put(f"{API_PREFIX}/groups/1", json=payload)

    assert create_response.status_code == 422
    assert update_response.status_code == 422


@pytest.mark.parametrize(
    "forbidden_fields",
    [
        {"project_id": 1},
        {"storage_cluster_id": 1},
        {"unexpected": True},
    ],
    ids=("project-id", "storage-cluster-id", "unexpected"),
)
def test_group_payload_forbids_derived_and_extra_fields(binding_api, forbidden_fields):
    create_response = binding_api.post(
        f"{API_PREFIX}/groups/",
        json={
            "name": "forbidden-field",
            "project_environment_id": 1,
            "volume_id": 1,
            **forbidden_fields,
        },
    )
    update_response = binding_api.put(
        f"{API_PREFIX}/groups/1",
        json={
            "project_environment_id": 1,
            "volume_id": 1,
            **forbidden_fields,
        },
    )

    assert create_response.status_code == 422
    assert update_response.status_code == 422


def test_group_create_and_update_persist_environment_target(binding_api, session_factory):
    created = binding_api.post(
        f"{API_PREFIX}/groups/",
        json={
            "name": "derived-create",
            "project_environment_id": 1,
            "volume_id": 1,
        },
    )
    assert created.status_code == 200

    updated = binding_api.put(
        f"{API_PREFIX}/groups/1",
        json={"project_environment_id": 2, "volume_id": 2},
    )
    assert updated.status_code == 200

    session = session_factory()
    try:
        created_group = session.query(models.Group).filter_by(name="derived-create").one()
        updated_group = session.get(models.Group, 1)
        assert created_group.project_environment_id == 1
        assert created_group.volume_id == 1
        assert created_group.qtree_id is None
        assert updated_group.project_environment_id == 2
        assert updated_group.volume_id == 2
        assert updated_group.qtree_id is None
    finally:
        session.close()


@pytest.mark.parametrize(
    ("filter_name", "filter_value"),
    [("project_id", 2), ("storage_cluster_id", 3)],
    ids=("project", "storage-cluster"),
)
def test_group_list_derives_project_and_cluster_filters_from_environment(
    binding_api, filter_name, filter_value
):
    response = binding_api.get(
        f"{API_PREFIX}/groups/",
        params={
            "nameLike": "environment-derived-filter-group",
            filter_name: filter_value,
            "page": 1,
            "size": 20,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["id"] for item in payload["content"]] == [5]


def test_group_list_filters_environment_and_returns_unified_targets(binding_api):
    response = binding_api.get(
        f"{API_PREFIX}/groups/",
        params={"project_environment_id": 1, "page": 1, "size": 20},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    groups_by_id = {item["id"]: item for item in payload["content"]}
    assert set(groups_by_id) == {1, 2}

    volume_group = groups_by_id[1]
    assert volume_group["project_environment"] == {"id": 1, "name": "environment-1"}
    assert volume_group["storage_cluster"] == {
        "id": 1,
        "name": "netapp-1",
        "storage_type": "netapp",
    }
    assert volume_group["storage_target"] == {
        "type": "volume",
        "id": 1,
        "name": "volume-1",
    }

    qtree_group = groups_by_id[2]
    assert qtree_group["storage_target"] == {
        "type": "qtree",
        "id": 1,
        "name": "qtree-1",
    }


def test_volume_target_response_does_not_query_qtree(binding_api, db_engine):
    statements = []

    def capture_statement(_connection, _cursor, statement, *_args):
        statements.append(statement.lower())

    event.listen(db_engine, "before_cursor_execute", capture_statement)
    try:
        response = binding_api.get(f"{API_PREFIX}/groups/1")
    finally:
        event.remove(db_engine, "before_cursor_execute", capture_statement)

    assert response.status_code == 200
    assert response.json()["storage_target"] == {
        "type": "volume",
        "id": 1,
        "name": "volume-1",
    }
    assert not any("qtrees" in statement for statement in statements)


@pytest.mark.parametrize(
    ("path", "resource"),
    [
        (f"{API_PREFIX}/storage-clusters/3", "cluster"),
        (f"{API_PREFIX}/volumes/4", "volume"),
        (f"{API_PREFIX}/qtrees/1", "qtree"),
    ],
    ids=("environment-or-group-cluster", "group-volume", "group-qtree"),
)
def test_referenced_storage_resources_cannot_be_deleted(binding_api, path, resource):
    try:
        response = binding_api.delete(path)
    except Exception as error:
        pytest.fail(
            f"{resource} delete must return a stable conflict response, "
            f"not raise {type(error).__name__}",
            pytrace=False,
        )

    assert response.status_code in {409, 422}
    assert resource in response.text.lower()
