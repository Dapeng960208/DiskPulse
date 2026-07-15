# -*- coding: utf-8 -*-
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from appConfig import base_config
from models import StorageCluster
from schemas.storageClusterSchema import StorageClusterCreate
from utils.isilonClient import IsilonClient


def _client(mode, *, path=None, redis_client=None):
    patches = [
        patch.object(IsilonClient, "_load_cached_session", return_value=True),
        patch.object(IsilonClient, "_probe", return_value=True),
    ]
    if redis_client is not None:
        patches.append(
            patch("utils.isilonClient.redis.StrictRedis", return_value=redis_client)
        )
    for active_patch in patches:
        active_patch.start()
    try:
        return IsilonClient(
            "storage.local",
            "svc",
            "secret",
            session_cache_mode=mode,
            session_cache_path=path,
        )
    finally:
        for active_patch in reversed(patches):
            active_patch.stop()


def test_storage_cluster_schema_and_model_persist_isilon_cache_settings(db_session):
    payload = StorageClusterCreate(
        name="isilon-a",
        storage_type="isilon",
        isilon_session_cache_mode="file",
        isilon_session_cache_path=".isilon_cache/custom.json",
    )
    cluster = StorageCluster(**payload.model_dump())
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)

    assert cluster.isilon_session_cache_mode == "file"
    assert cluster.isilon_session_cache_path == ".isilon_cache/custom.json"


def test_storage_cluster_schema_rejects_unknown_isilon_cache_mode():
    with pytest.raises(ValueError):
        StorageClusterCreate(
            name="isilon-a",
            storage_type="isilon",
            isilon_session_cache_mode="memory",
        )


def test_file_cache_uses_configured_path_and_persists_session(tmp_path):
    cache_path = tmp_path / "sessions" / "onefs.json"
    client = _client("file", path=str(cache_path))
    client.session.cookies.set("isisessid", "cookie-value")
    client.session.headers["X-CSRF-Token"] = "csrf-value"

    assert client._save_session_cache(120) is True
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert payload[client._cache_key]["cookies"]["isisessid"] == "cookie-value"
    assert payload[client._cache_key]["csrf"] == "csrf-value"


def test_redis_cache_uses_existing_redis_config_and_ttl():
    redis_client = Mock()
    base_config.set("redis.host", "redis.local")
    base_config.set("redis.port", 6380)
    base_config.set("redis.session_db", 8)
    client = _client("redis", redis_client=redis_client)
    client.session.cookies.set("isisessid", "cookie-value")

    assert client._save_session_cache(120) is True
    redis_client.setex.assert_called_once()
    assert redis_client.setex.call_args.args[1] == 120


def test_no_cache_logs_out_and_releases_session():
    with (
        patch.object(IsilonClient, "_load_cached_session", return_value=False),
        patch.object(IsilonClient, "_login", return_value=True),
        patch.object(IsilonClient, "_probe", return_value=True),
    ):
        client = IsilonClient(
            "storage.local",
            "svc",
            "secret",
            session_cache_mode="none",
        )
    client.session.delete = Mock()
    client.session.close = Mock()

    client.close()

    client.session.delete.assert_called_once_with(client._session_url, timeout=15)
    client.session.close.assert_called_once_with()


def test_failed_cache_write_logs_out_instead_of_leaking_session():
    redis_client = Mock()
    redis_client.setex.side_effect = RuntimeError("redis unavailable")
    client = _client("redis", redis_client=redis_client)
    client.session.cookies.set("isisessid", "cookie-value")

    assert client._save_session_cache(120) is False
    client.session.delete = Mock()
    client.session.close = Mock()
    client.close()

    client.session.delete.assert_called_once_with(client._session_url, timeout=15)

