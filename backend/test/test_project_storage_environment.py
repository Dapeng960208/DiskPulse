# -*- coding: utf-8 -*-
import importlib
import importlib.util
import re
from datetime import datetime

import pytest
from fastapi import APIRouter

from appConfig import base_config
from main import app
import models
from routers import projects
from utils.security import issue_token


API_PREFIX = "/storage-pulse/api"
PROJECT_ENVIRONMENTS = f"{API_PREFIX}/projects/1/storage-environments"
ENVIRONMENTS = f"{API_PREFIX}/storage-environments"
NOW = datetime.fromisoformat("2026-07-13T10:00:00")


def _environment_router() -> APIRouter:
    module_name = "routers.project_storage_environment"
    if importlib.util.find_spec(module_name) is None:
        return APIRouter()
    return importlib.import_module(module_name).router


@pytest.fixture
def environment_api(api_client_factory, session_factory):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        session.add_all(
            [
                models.User(id=1, rd_username="admin", username="Admin"),
                models.User(id=2, rd_username="lead", username="Lead"),
                models.User(id=3, rd_username="pt", username="PT"),
                models.User(id=4, rd_username="outsider", username="Outsider"),
                models.Project(
                    id=1,
                    name="alpha",
                    in_charge_user_id=2,
                    pt_user_id=3,
                ),
                *[
                    models.StorageCluster(
                        id=cluster_id,
                        name=f"cluster-{cluster_id}",
                        storage_type="netapp",
                        storage_host=f"storage-{cluster_id}.internal",
                        storage_user="collector",
                        storage_password="secret",
                    )
                    for cluster_id in range(1, 5)
                ],
                *[
                    models.ProjectStorageEnvironment(
                        id=environment_id,
                        project_id=1,
                        storage_cluster_id=environment_id,
                        name=f"environment-{environment_id}",
                        description=f"environment {environment_id}",
                        is_active=True,
                        collection_status="pending",
                        created_at=NOW,
                        updated_at=NOW,
                    )
                    for environment_id in (3, 1, 2)
                ],
                models.Group(
                    id=1,
                    project_id=1,
                    project_environment_id=1,
                    storage_cluster_id=1,
                    name="linked-group",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    return api_client_factory(
        [projects.router, _environment_router()],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )


def _headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_token(user_id)}"}


def _assert_error(response, status_code: int, resource: str) -> None:
    assert response.status_code == status_code
    assert resource in response.text.lower()


def _normalized_routes() -> set[tuple[str, str]]:
    return {
        (method, re.sub(r"\{[^}]+\}", "{}", route.path))
        for route in app.routes
        for method in getattr(route, "methods", set())
    }


def test_storage_environment_routes_are_registered_with_expected_methods():
    routes = _normalized_routes()

    assert {
        ("GET", f"{API_PREFIX}/projects/{{}}/storage-environments"),
        ("POST", f"{API_PREFIX}/projects/{{}}/storage-environments"),
        ("GET", f"{ENVIRONMENTS}/{{}}"),
        ("PUT", f"{ENVIRONMENTS}/{{}}"),
        ("DELETE", f"{ENVIRONMENTS}/{{}}"),
    } <= routes


def test_storage_environment_http_methods_and_pagination(environment_api):
    listed = environment_api.get(
        PROJECT_ENVIRONMENTS,
        params={"page": 1, "size": 2},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 3
    assert [item["id"] for item in listed.json()["content"]] == [1, 2]

    created = environment_api.post(
        PROJECT_ENVIRONMENTS,
        json={
            "name": "  production  ",
            "storage_cluster_id": 4,
            "description": "Production storage",
            "is_active": False,
        },
    )
    assert created.status_code == 201
    environment_id = created.json()["id"]

    fetched = environment_api.get(f"{ENVIRONMENTS}/{environment_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "production"

    updated = environment_api.put(
        f"{ENVIRONMENTS}/{environment_id}",
        json={"name": "production-renamed", "description": None, "is_active": True},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "production-renamed"

    deleted = environment_api.delete(f"{ENVIRONMENTS}/{environment_id}")
    assert deleted.status_code == 204


def test_storage_environment_response_does_not_leak_cluster_credentials(environment_api):
    response = environment_api.get(f"{ENVIRONMENTS}/1")

    assert response.status_code == 200
    payload = response.json()
    assert {
        "id",
        "project_id",
        "storage_cluster_id",
        "name",
        "description",
        "is_active",
        "limit",
        "soft_limit",
        "used",
        "use_ratio",
        "soft_use_ratio",
        "collection_status",
        "last_collected_at",
        "created_at",
        "updated_at",
        "storage_cluster",
    } <= payload.keys()
    assert set(payload["storage_cluster"]) == {"id", "name", "storage_type"}


def test_storage_environment_permissions(environment_api):
    for user_id in (1, 2, 3):
        assert environment_api.get(
            PROJECT_ENVIRONMENTS,
            headers=_headers(user_id),
        ).status_code == 200
        assert environment_api.get(
            f"{ENVIRONMENTS}/1",
            headers=_headers(user_id),
        ).status_code == 200

    for path in (PROJECT_ENVIRONMENTS, f"{ENVIRONMENTS}/1"):
        assert environment_api.get(path, headers=_headers(4)).status_code == 403

    assert environment_api.post(
        PROJECT_ENVIRONMENTS,
        json={"name": "forbidden", "storage_cluster_id": 4},
        headers=_headers(2),
    ).status_code == 403
    assert environment_api.put(
        f"{ENVIRONMENTS}/1",
        json={"name": "forbidden"},
        headers=_headers(2),
    ).status_code == 403
    assert environment_api.delete(
        f"{ENVIRONMENTS}/1",
        headers=_headers(2),
    ).status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   ", "storage_cluster_id": 4},
        {"name": "x" * 129, "storage_cluster_id": 4},
        {"name": "valid", "storage_cluster_id": 4, "unexpected": True},
        {"name": "missing-cluster"},
    ],
    ids=("blank-name", "long-name", "extra-field", "missing-cluster"),
)
def test_create_storage_environment_rejects_invalid_payload(environment_api, payload):
    response = environment_api.post(PROJECT_ENVIRONMENTS, json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": "x" * 129},
        {"storage_cluster_id": 4},
        {"unexpected": True},
    ],
    ids=("blank-name", "long-name", "immutable-cluster", "extra-field"),
)
def test_update_storage_environment_rejects_invalid_payload(environment_api, payload):
    response = environment_api.put(f"{ENVIRONMENTS}/1", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0, "size": 10},
        {"page": 1, "size": 0},
        {"page": 1, "size": 101},
    ],
    ids=("page-below-one", "size-below-one", "size-above-one-hundred"),
)
def test_list_storage_environments_validates_pagination(environment_api, params):
    response = environment_api.get(PROJECT_ENVIRONMENTS, params=params)

    assert response.status_code == 422


def test_storage_environment_missing_resources_return_404(environment_api):
    _assert_error(
        environment_api.get(f"{API_PREFIX}/projects/999/storage-environments"),
        404,
        "project",
    )
    _assert_error(environment_api.get(f"{ENVIRONMENTS}/999"), 404, "environment")
    _assert_error(
        environment_api.post(
            PROJECT_ENVIRONMENTS,
            json={"name": "missing-cluster", "storage_cluster_id": 999},
        ),
        404,
        "cluster",
    )


@pytest.mark.parametrize(
    ("payload", "conflict_resource"),
    [
        ({"name": " environment-1 ", "storage_cluster_id": 4}, "name"),
        ({"name": "unique-name", "storage_cluster_id": 1}, "cluster"),
    ],
    ids=("project-name", "project-cluster"),
)
def test_create_storage_environment_returns_409_for_duplicates(
    environment_api,
    payload,
    conflict_resource,
):
    response = environment_api.post(PROJECT_ENVIRONMENTS, json=payload)

    _assert_error(response, 409, conflict_resource)


def test_delete_storage_environment_with_linked_group_returns_409(environment_api):
    response = environment_api.delete(f"{ENVIRONMENTS}/1")

    _assert_error(response, 409, "group")
