# -*- coding: utf-8 -*-
from unittest.mock import Mock

import pytest
import requests

import models
from scripts.manual_isilon_check import fetch_quota_summary, load_isilon_config


def test_load_isilon_config_reads_named_database_cluster(db_session):
    db_session.add(
        models.StorageCluster(
            name="isilon-a",
            storage_type="isilon",
            storage_host="storage.local",
            storage_port=8080,
            storage_user="collector",
            storage_password="secret",
            is_active=True,
        )
    )
    db_session.commit()

    config = load_isilon_config(db_session, "isilon-a")

    assert config == {
        "name": "isilon-a",
        "host": "storage.local",
        "port": 8080,
        "username": "collector",
        "password": "secret",
    }


def test_fetch_quota_summary_uses_configured_client_and_closes_it():
    client = Mock()
    client.get_quotas.return_value = [
        {"type": "directory"},
        {"type": "user"},
        {"type": "directory"},
    ]
    client_factory = Mock(return_value=client)
    config = {
        "name": "isilon-a",
        "host": "storage.local",
        "port": 8080,
        "username": "collector",
        "password": "secret",
    }

    summary = fetch_quota_summary(
        config,
        tls_verify=False,
        client_factory=client_factory,
    )

    assert summary == {"total": 3, "types": {"directory": 2, "user": 1}}
    client_factory.assert_called_once_with(
        "storage.local",
        "collector",
        "secret",
        port=8080,
        tls_verify=False,
    )
    client.close.assert_called_once_with()


def test_fetch_quota_summary_closes_client_when_request_fails():
    client = Mock()
    client.get_quotas.side_effect = requests.ConnectionError("offline")

    with pytest.raises(requests.ConnectionError, match="offline"):
        fetch_quota_summary(
            {
                "name": "isilon-a",
                "host": "storage.local",
                "port": 8080,
                "username": "collector",
                "password": "secret",
            },
            tls_verify=True,
            client_factory=Mock(return_value=client),
        )

    client.close.assert_called_once_with()
