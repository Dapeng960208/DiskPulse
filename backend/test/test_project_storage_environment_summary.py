# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import Mock

import pytest

from appConfig import base_config
from crud import questDbCrud
import models
from routers import project_storage_environment
from utils.security import issue_token


API_PREFIX = "/storage-pulse/api/storage-environments"
NOW = datetime.fromisoformat("2026-07-13T10:00:00")
START = datetime.fromisoformat("2026-07-12T10:00:00")
END = datetime.fromisoformat("2026-07-13T10:00:00")
SERIES = [["2026-07-13 09:59:00", 400.0]]
CLUSTER_PRIVATE_FIELDS = {
    "storage_host",
    "storage_port",
    "storage_user",
    "storage_password",
}


def _headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_token(user_id)}"}


def _nested_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_nested_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_nested_keys(item) for item in value))
    return set()


@pytest.fixture
def summary_api(api_client_factory, session_factory, monkeypatch):
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
                models.StorageCluster(
                    id=1,
                    name="cluster-1",
                    storage_type="netapp",
                    storage_host="storage.test",
                    storage_user="test-user",
                    storage_password="test-password",
                ),
                models.ProjectStorageEnvironment(
                    id=1,
                    project_id=1,
                    storage_cluster_id=1,
                    name="production",
                    limit=1000,
                    soft_limit=800,
                    used=400,
                    use_ratio=40,
                    soft_use_ratio=50,
                    collection_status="success",
                    last_collected_at=NOW,
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    realtime_mock = Mock(return_value=SERIES)
    monkeypatch.setattr(questDbCrud, "get_real_time_data_by_id", realtime_mock)
    client = api_client_factory(
        [project_storage_environment.router],
        headers=_headers(1),
    )
    return client, realtime_mock


def test_storage_environment_summary_returns_current_state_without_credentials(
    summary_api,
):
    client, _realtime_mock = summary_api

    response = client.get(f"{API_PREFIX}/1/summary")

    assert response.status_code == 200
    payload = response.json()
    assert {
        "id": 1,
        "name": "production",
        "limit": 1000,
        "soft_limit": 800,
        "used": 400,
        "use_ratio": 40,
        "soft_use_ratio": 50,
        "collection_status": "success",
        "last_collected_at": NOW.isoformat(),
    }.items() <= payload.items()
    assert payload["storage_cluster"] == {
        "id": 1,
        "name": "cluster-1",
        "storage_type": "netapp",
    }
    assert CLUSTER_PRIVATE_FIELDS.isdisjoint(_nested_keys(payload))


def test_storage_environment_realtime_returns_info_and_environment_series(summary_api):
    client, realtime_mock = summary_api

    response = client.get(
        f"{API_PREFIX}/1/realtime",
        params={
            "start_time": START.isoformat(),
            "end_time": END.isoformat(),
            "indicator": "used",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == SERIES
    assert {
        "id": 1,
        "name": "production",
        "limit": 1000,
        "soft_limit": 800,
        "used": 400,
        "use_ratio": 40,
        "soft_use_ratio": 50,
        "collection_status": "success",
        "last_collected_at": NOW.isoformat(),
    }.items() <= payload["info"].items()
    assert CLUSTER_PRIVATE_FIELDS.isdisjoint(_nested_keys(payload))
    realtime_mock.assert_called_once()
    call = realtime_mock.call_args.kwargs
    assert call["attribute_id"] == 1
    assert call["start_time"] == START
    assert call["end_time"] == END
    assert call["indicator"] == "used"
    assert call["table_prefix"] == "project_environment"


@pytest.mark.parametrize("suffix", ("summary", "realtime"))
def test_storage_environment_read_permissions_match_detail(summary_api, suffix):
    client, _realtime_mock = summary_api
    path = f"{API_PREFIX}/1/{suffix}"

    for user_id in (1, 2, 3):
        assert client.get(path, headers=_headers(user_id)).status_code == 200
    assert client.get(path, headers=_headers(4)).status_code == 403


@pytest.mark.parametrize("suffix", ("summary", "realtime"))
def test_storage_environment_summary_and_realtime_return_404_when_missing(
    summary_api,
    suffix,
):
    client, _realtime_mock = summary_api

    response = client.get(f"{API_PREFIX}/999/{suffix}")

    assert response.status_code == 404
    assert "environment" in response.text.lower()
