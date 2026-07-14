# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch

import pytest
import requests

import models
from scripts.manual_isilon_check import fetch_quota_summary, load_isilon_config, main


def test_load_isilon_config_reads_named_database_cluster(db_session):
    db_session.add(
        models.StorageCluster(
            name="isilon-a",
            storage_type="isilon",
            storage_host="storage.local",
            storage_port=8080,
            storage_user="collector",
            storage_password="secret",
            protocol="http",
            tls_verify=False,
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
        "protocol": "http",
        "tls_verify": False,
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
        "protocol": "http",
        "tls_verify": False,
    }

    summary = fetch_quota_summary(config, client_factory=client_factory)

    assert summary == {"total": 3, "types": {"directory": 2, "user": 1}}
    client_factory.assert_called_once_with(
        "storage.local",
        "collector",
        "secret",
        port=8080,
        protocol="http",
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
                "protocol": "https",
                "tls_verify": True,
            },
            client_factory=Mock(return_value=client),
        )

    client.close.assert_called_once_with()


def test_main_passes_database_transport_config_without_yaml_override():
    config = {
        "name": "isilon-a",
        "host": "storage.local",
        "port": 8080,
        "username": "collector",
        "password": "secret",
        "protocol": "http",
        "tls_verify": False,
    }
    session_context = Mock()
    session_context.__enter__ = Mock(return_value=Mock())
    session_context.__exit__ = Mock(return_value=False)

    with (
        patch("scripts.manual_isilon_check.SessionLocal", return_value=session_context),
        patch("scripts.manual_isilon_check.load_isilon_config", return_value=config),
        patch(
            "scripts.manual_isilon_check.fetch_quota_summary",
            return_value={"total": 1, "types": {"directory": 1}},
        ) as fetch_summary,
    ):
        assert main(["isilon-a"]) == 0

    fetch_summary.assert_called_once_with(config)
