# -*- coding: utf-8 -*-
from pathlib import Path

import pytest

from appConfig import Config


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _write_config(
    path: Path,
    ldap_flags: str = "lookup_user_dn: true\n  lookup_as_user: false",
) -> Path:
    path.write_text(
        f"""
application:
  mode: test
  company_name: DiskPulse
  cors_origins:
    - http://localhost:5173
database:
  create_tables: false
  postgres:
    host: db.example.com
    port: 5432
    name: diskpulse
    user: diskpulse
    password: "p@ss:/word"
    pool_size: 20
    max_overflow: 10
    pool_timeout: 10
  questdb:
    host: quest.example.com
    port: 8812
    user: admin
    password: "quest@word"
    pool_size: 20
    max_overflow: 0
    pool_timeout: 60
    pool_recycle: 300
redis:
  host: redis.example.com
  port: 6379
  session_db: 8
jwt:
  secret_key: yaml-secret
  access_ttl_minutes: 60
ldap:
  uri: ldap://dc.com
  starttls: true
  timeout_seconds: 5
  bind_dn: CN=Service,OU=IT,DC=dc,DC=com
  bind_password_file: ./ldap-password.dev
  user_bases:
    - OU=DC,DC=dc,DC=com
  group_bases:
    - OU=DC,DC=dc,DC=com
  user_class: user
  user_name_attribute: sAMAccountName
  user_fullname_attribute: cn
  user_extra_filters:
    - (!(objectClass=computer))
    - (!(objectClass=group))
  {ldap_flags}
super_admin_usernames:
  - guojianpeng
""".strip(),
        encoding="utf-8",
    )
    return path


def test_loads_grouped_yaml_without_environment_override(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "environment-secret")
    config = Config(_write_config(tmp_path / "config.yml"))

    assert config.get("application.mode") == "test"
    assert config.get("database.create_tables") is False
    assert config.get("application.cors_origins") == ["http://localhost:5173"]
    assert config.get("jwt.secret_key") == "yaml-secret"
    assert config.get("super_admin_usernames") == ["guojianpeng"]
    assert config.get_sqlalchemy_database_url() == (
        "postgresql+psycopg2://diskpulse:p%40ss%3A%2Fword@db.example.com:5432/diskpulse"
    )
    assert config.get_quest_db_url() == (
        "questdb://admin:quest%40word@quest.example.com:8812/qdb?timezone=UTC"
    )


def test_resolves_secret_file_relative_to_yaml(tmp_path):
    config_path = _write_config(tmp_path / "config.yml")
    config = Config(config_path)

    assert config.resolve_path("ldap.bind_password_file") == tmp_path / "ldap-password.dev"


@pytest.mark.parametrize(
    "ldap_flags",
    [
        "lookup_user_dn: false\n  lookup_as_user: false",
        "lookup_user_dn: true\n  lookup_as_user: true",
    ],
)
def test_rejects_unsupported_ldap_lookup_modes(tmp_path, ldap_flags):
    with pytest.raises(ValueError, match="lookup_user_dn=true and lookup_as_user=false"):
        Config(_write_config(tmp_path / "config.yml", ldap_flags))


@pytest.mark.parametrize("content", ["- invalid-root", "ldap: ["])
def test_rejects_invalid_yaml(tmp_path, content):
    config_path = tmp_path / "config.yml"
    config_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid YAML configuration"):
        Config(config_path)


def test_rejects_missing_yaml_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        Config(tmp_path / "missing.yml")


def test_example_storage_config_does_not_define_global_tls_verification():
    config = Config(BACKEND_ROOT / "config.example.yml")

    assert config.get("storage.tls_verify") is None
    assert config.get("storage.isilon_session_cache") is None
    assert config.get("redis.session_db") == 8
