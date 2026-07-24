# -*- coding: utf-8 -*-
import base64
import hmac
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from fastapi import APIRouter

from appConfig import base_config
import models
from celery_tasks.manager.remoteFileManager import RemoteFileManager
from routers import common, config, storage_cluster
from utils.netAppClient import NetAppClient
from utils.isilonClient import IsilonClient
from utils.security import decode_token, issue_token


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def seed_security_data(session_factory):
    session = session_factory()
    try:
        session.add(
            models.User(
                id=1,
                rd_username="secadmin",
                username="Security Admin",
                user_type=1,
                is_alert=True,
            )
        )
        session.add(
            models.User(
                id=2,
                rd_username="viewer",
                username="Viewer",
                user_type=2,
                is_alert=True,
            )
        )
        session.add(
            models.StorageConf(
                name="storage conf",
                mail_user="mail-user",
                mail_password="mail-secret",
                file_manage_user="file-user",
                file_manage_password="file-secret",
            )
        )
        session.add(
            models.StorageCluster(
                name="cluster-a",
                storage_type="netapp",
                storage_host="storage.local",
                storage_port=443,
                storage_user="svc",
                storage_password="cluster-secret",
            )
        )
        session.commit()
    finally:
        session.close()


def security_route_setup(storage_router: APIRouter):
    @storage_router.get("/boom")
    @common.handle_exceptions
    def boom():
        raise RuntimeError("secret-token-value")


@pytest.fixture
def security_client(api_client_factory, session_factory):
    base_config.set("jwt.secret_key", "test-jwt-secret-key-for-unit-tests-32")
    base_config.set("super_admin_usernames", ["secadmin"])
    seed_security_data(session_factory)
    client = api_client_factory(
        [config.router, storage_cluster.router],
        authenticated=True,
        route_setup=security_route_setup,
    )
    return client


def test_config_response_redacts_secret_fields(security_client):
    response = security_client.get(
        "/storage-pulse/api/config/storage",
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    assert response.status_code == 200
    payload = response.json()
    for key in (
        "iam_password",
        "mail_password",
        "storage_password",
        "file_manage_password",
    ):
        assert key not in payload
    assert "secret" not in response.text


def test_storage_cluster_response_redacts_password(security_client):
    response = security_client.get(
        "/storage-pulse/api/storage-clusters/1",
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    assert response.status_code == 200
    assert "storage_password" not in response.json()
    assert "cluster-secret" not in response.text


def test_exception_handler_does_not_return_internal_exception_text(security_client):
    response = security_client.get(
        "/storage-pulse/api/boom",
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert "secret-token-value" not in response.text


def test_jwt_decoder_rejects_unexpected_header_algorithm():
    base_config.set("jwt.secret_key", "test-jwt-secret-key-for-unit-tests-32")
    token = issue_token(1)
    _header, encoded_payload, _signature = token.split(".")
    encoded_header = _b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    message = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _b64encode(hmac.new(b"test-jwt-secret-key-for-unit-tests-32", message, "sha256").digest())

    with pytest.raises(Exception):
        decode_token(f"{encoded_header}.{encoded_payload}.{signature}")


def test_netapp_client_verifies_tls_by_default():
    client = NetAppClient("storage.local", "svc", "secret")

    assert client.session.verify is True


def test_netapp_client_uses_configured_protocol_for_base_and_next_urls():
    client = NetAppClient(
        "storage.local",
        "svc",
        "secret",
        port=80,
        protocol="http",
    )
    first_response = Mock()
    first_response.json.return_value = {
        "records": [],
        "_links": {"next": {"href": "/api/storage/volumes?start=2"}},
    }
    second_response = Mock()
    second_response.json.return_value = {"records": []}
    client.session.get = Mock(side_effect=[first_response, second_response])

    client.get_volumes()

    assert [item.args[0] for item in client.session.get.call_args_list] == [
        "http://storage.local:80/api/storage/volumes",
        "http://storage.local:80/api/storage/volumes?start=2",
    ]


def test_netapp_client_propagates_connection_failure():
    client = NetAppClient("storage.local", "svc", "secret", tls_verify=False)
    client.session.get = Mock(side_effect=requests.ConnectionError("unavailable"))

    with pytest.raises(requests.ConnectionError, match="unavailable"):
        client.get_volumes()


def test_netapp_client_preserves_native_http_error_response():
    logger = Mock()
    client = NetAppClient(
        "storage.local", "svc", "secret", logger=logger, tls_verify=False
    )
    response = requests.Response()
    response.status_code = 403
    response.headers["content-type"] = "application/json"
    response._content = b'{"error":{"code":"forbidden","message":"write required"}}'
    client.session.get = Mock(return_value=response)

    with pytest.raises(requests.HTTPError) as error:
        client.get_volumes()

    assert error.value.response is response
    assert error.value.response.status_code == 403
    assert error.value.response.content == response.content
    assert "device_status=403" in logger.error.call_args_list[0].args[0]
    assert "write required" in logger.error.call_args_list[0].args[0]


def test_netapp_qtree_request_omits_unsupported_oplocks_field():
    client = NetAppClient("storage.local", "svc", "secret")
    client._get_all_records = Mock(return_value=[])

    client.get_qtrees()

    fields = client._get_all_records.call_args.kwargs["params"]["fields"].split(",")
    assert "oplocks" not in fields


def test_isilon_client_propagates_connection_failure():
    client = object.__new__(IsilonClient)
    client.base_url = "https://storage.local:8080/platform"
    client.session = Mock()
    client.session.get.side_effect = requests.ConnectionError("unavailable")
    client._log = Mock()

    with pytest.raises(requests.ConnectionError, match="unavailable"):
        client._get("/1/cluster/statfs")


@pytest.mark.parametrize("method_name, request_method", [("_login", "post"), ("_probe", "get")])
def test_isilon_session_setup_preserves_native_http_error_response(
    method_name, request_method
):
    client = object.__new__(IsilonClient)
    client.base_url = "https://storage.local:8080/platform"
    client._session_url = "https://storage.local:8080/session/1/session"
    client.session = Mock()
    client._log = Mock()
    client.username = "svc"
    client.password = "secret"
    response = requests.Response()
    response.status_code = 403
    response.headers["content-type"] = "application/json"
    response._content = b'{"errors":[{"message":"Quota write privilege is required"}]}'
    getattr(client.session, request_method).return_value = response

    with pytest.raises(requests.HTTPError) as error:
        getattr(client, method_name)()

    assert error.value.response is response
    assert error.value.response.status_code == 403
    assert error.value.response.content == response.content


def test_isilon_cached_session_validation_preserves_unrecoverable_http_error():
    client = object.__new__(IsilonClient)
    client._session_cache_enabled = True
    client._session_url = "https://storage.local:8080/session/1/session"
    client._cache_key = "https:storage.local:8080:svc"
    client.session = Mock()
    client._read_cache = Mock(return_value={client._cache_key: {"cookies": {}}})
    client._apply_cookies = Mock()
    client._log = Mock()
    response = requests.Response()
    response.status_code = 503
    response.headers["content-type"] = "application/json"
    response._content = b'{"message":"cluster service unavailable"}'
    client.session.get.return_value = response

    with pytest.raises(requests.HTTPError) as error:
        client._load_cached_session()

    assert error.value.response is response
    assert error.value.response.content == response.content


def test_isilon_client_uses_configured_protocol_for_all_session_urls():
    with (
        patch.object(IsilonClient, "_load_cached_session", return_value=True),
        patch.object(IsilonClient, "_probe", return_value=True),
    ):
        client = IsilonClient(
            "storage.local",
            "svc",
            "secret",
            port=8080,
            protocol="http",
        )

    assert client.base_url == "http://storage.local:8080/platform"
    assert client._session_url == "http://storage.local:8080/session/1/session"
    assert client._cache_key == "http:storage.local:8080:svc"

    client._apply_cookies({"csrf": "cached-token"})
    assert client.session.headers["Referer"] == "http://storage.local:8080/"

    response = Mock(ok=True, status_code=201)
    response.json.return_value = {}
    client.session.post = Mock(return_value=response)
    client.session.cookies.set("isicsrf", "fresh-token")
    assert client._login() is True
    assert client.session.headers["Referer"] == "http://storage.local:8080/"


def test_remote_file_manager_quotes_shell_path_arguments():
    class FakeSSH:
        def __init__(self):
            self.commands = []

        def exec_command(self, command):
            self.commands.append(command)

            class Stream:
                def read(self):
                    return b""

            return None, Stream(), Stream()

    manager = object.__new__(RemoteFileManager)
    manager.client = type("Client", (), {"ssh": FakeSSH()})()
    manager.logger = type(
        "Logger",
        (),
        {"error": lambda *args: None, "info": lambda *args: None, "warning": lambda *args: None},
    )()

    manager.create_directory("/data/a path; rm -rf /")

    command = manager.client.ssh.commands[-1]
    assert "'/data/a path; rm -rf /'" in command
    assert "mkdir -p /data/a path; rm -rf /" not in command


def test_bare_authorization_token_is_rejected(security_client):
    base_config.set("jwt.secret_key", "test-jwt-secret-key-for-unit-tests-32")
    admin_token = issue_token(1)
    response = security_client.get(
        "/storage-pulse/api/storage-clusters/1",
        headers={"Authorization": admin_token},
    )

    assert response.status_code == 401


def test_sensitive_config_requires_super_admin(security_client):
    response = security_client.get(
        "/storage-pulse/api/config/storage",
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )

    assert response.status_code == 403


def test_authenticated_users_can_read_only_storage_alert_thresholds(security_client):
    response = security_client.get(
        "/storage-pulse/api/config/storage-alert-thresholds",
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "important": 80,
        "serious": 90,
        "emergency": 95,
    }


def test_storage_alert_thresholds_require_authentication(security_client):
    response = security_client.get(
        "/storage-pulse/api/config/storage-alert-thresholds",
    )

    assert response.status_code == 401


def test_manual_integration_checks_are_not_collected_as_unit_tests():
    assert not (BACKEND_ROOT / "test" / "test_netapp.py").exists()
    assert not (BACKEND_ROOT / "test" / "test_isilon.py").exists()


def test_backend_sources_do_not_contain_legacy_product_or_personal_contact_defaults():
    forbidden = (
        "disk-monitor.engiant.com",
        "guo.jianpeng@engiant.com",
        "Disk Monitor",
        "engiant.com",
        "grandtrans.com",
        "gention.com",
    )
    scanned = []
    for path in BACKEND_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".html", ".txt"}:
            continue
        if path.parts[-2:] == ("test", "test_security_regressions.py"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for value in forbidden:
            if value in text:
                scanned.append(f"{path.relative_to(BACKEND_ROOT)} contains {value}")

    assert scanned == []
