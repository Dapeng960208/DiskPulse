# -*- coding: utf-8 -*-
from datetime import datetime

import pytest

from appConfig import base_config
import models
from routers import projects
from utils.security import issue_token


API_PATH = "/storage-pulse/api/projects/"
NOW = datetime.fromisoformat("2026-07-13T10:00:00")
CLUSTER_PRIVATE_FIELDS = {
    "storage_host",
    "storage_port",
    "storage_user",
    "storage_password",
}


def _nested_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_nested_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_nested_keys(item) for item in value))
    return set()


@pytest.fixture
def overview_api(api_client_factory, session_factory):
    base_config.set("jwt.secret_key", "test-secret")
    session = session_factory()
    try:
        session.add(models.User(id=1, rd_username="reader", username="Reader"))
        session.add_all(
            [
                models.Project(
                    id=1,
                    name="alpha",
                    limit=900,
                    soft_limit=720,
                    used=360,
                    use_ratio=40,
                    soft_use_ratio=50,
                ),
                models.Project(
                    id=2,
                    name="beta",
                    limit=200,
                    soft_limit=160,
                    used=80,
                    use_ratio=40,
                    soft_use_ratio=50,
                ),
                models.Project(id=3, name="empty", limit=0, used=0),
                *[
                    models.StorageCluster(
                        id=cluster_id,
                        name=f"cluster-{cluster_id}",
                        storage_type=storage_type,
                        storage_host=f"storage-{cluster_id}.test",
                        storage_user="test-user",
                        storage_password="test-password",
                    )
                    for cluster_id, storage_type in (
                        (1, "netapp"),
                        (2, "isilon"),
                        (3, "netapp"),
                        (4, "isilon"),
                    )
                ],
            ]
        )
        session.flush()
        session.add_all(
            [
                models.ProjectStorageEnvironment(
                    id=1,
                    project_id=1,
                    storage_cluster_id=1,
                    name="alpha-pending",
                    is_active=True,
                    limit=10,
                    used=1,
                    collection_status="pending",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.ProjectStorageEnvironment(
                    id=2,
                    project_id=1,
                    storage_cluster_id=2,
                    name="alpha-success",
                    is_active=True,
                    limit=20,
                    used=2,
                    collection_status="success",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.ProjectStorageEnvironment(
                    id=3,
                    project_id=1,
                    storage_cluster_id=3,
                    name="alpha-failed",
                    is_active=True,
                    limit=30,
                    used=3,
                    collection_status="failed",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.ProjectStorageEnvironment(
                    id=4,
                    project_id=1,
                    storage_cluster_id=4,
                    name="alpha-inactive",
                    is_active=False,
                    limit=40,
                    used=4,
                    collection_status="success",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.ProjectStorageEnvironment(
                    id=5,
                    project_id=2,
                    storage_cluster_id=1,
                    name="beta-success",
                    is_active=True,
                    limit=500,
                    used=250,
                    collection_status="success",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    return api_client_factory(
        [projects.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )


def test_project_list_includes_isolated_storage_environment_overviews(overview_api):
    response = overview_api.get(API_PATH, params={"page": 1, "size": 20})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    projects_by_id = {item["id"]: item for item in payload["content"]}
    assert {
        project_id: {
            "storage_environment_count": project["storage_environment_count"],
            "active_storage_environment_count": project[
                "active_storage_environment_count"
            ],
            "storage_cluster_types": project["storage_cluster_types"],
            "storage_environment_status_counts": project[
                "storage_environment_status_counts"
            ],
        }
        for project_id, project in projects_by_id.items()
    } == {
        1: {
            "storage_environment_count": 4,
            "active_storage_environment_count": 3,
            "storage_cluster_types": ["isilon", "netapp"],
            "storage_environment_status_counts": {
                "pending": 1,
                "success": 1,
                "failed": 1,
                "inactive": 1,
            },
        },
        2: {
            "storage_environment_count": 1,
            "active_storage_environment_count": 1,
            "storage_cluster_types": ["netapp"],
            "storage_environment_status_counts": {
                "pending": 0,
                "success": 1,
                "failed": 0,
                "inactive": 0,
            },
        },
        3: {
            "storage_environment_count": 0,
            "active_storage_environment_count": 0,
            "storage_cluster_types": [],
            "storage_environment_status_counts": {
                "pending": 0,
                "success": 0,
                "failed": 0,
                "inactive": 0,
            },
        },
    }


def test_project_list_keeps_persisted_capacity_snapshot(overview_api):
    response = overview_api.get(API_PATH)

    assert response.status_code == 200
    projects_by_id = {item["id"]: item for item in response.json()["content"]}
    assert {
        key: projects_by_id[1][key]
        for key in ("limit", "soft_limit", "used", "use_ratio", "soft_use_ratio")
    } == {
        "limit": 900,
        "soft_limit": 720,
        "used": 360,
        "use_ratio": 40,
        "soft_use_ratio": 50,
    }


def test_project_list_does_not_expose_storage_cluster_credentials(overview_api):
    response = overview_api.get(API_PATH)

    assert response.status_code == 200
    assert CLUSTER_PRIVATE_FIELDS.isdisjoint(_nested_keys(response.json()))
