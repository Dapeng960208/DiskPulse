# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import yaml


APP_ROOT_PATH = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = APP_ROOT_PATH / "config.yml"


class Config:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
        self.config: dict[str, Any] = {}
        self._loaded = False
        if path is not None:
            self.load()

    def load(self, path: str | Path | None = None) -> None:
        if path is not None:
            self.path = Path(path)
        try:
            loaded = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"Configuration file not found: {self.path}") from error
        except yaml.YAMLError as error:
            raise ValueError(f"Invalid YAML configuration: {self.path}") from error
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid YAML configuration: root must be a mapping: {self.path}")

        ldap = loaded.get("ldap")
        if isinstance(ldap, dict) and (
            ldap.get("lookup_user_dn") is not True or ldap.get("lookup_as_user") is not False
        ):
            raise ValueError("LDAP requires lookup_user_dn=true and lookup_as_user=false")

        feishu = loaded.get("feishu_notification")
        if isinstance(feishu, dict) and feishu.get("enabled"):
            missing = [key for key in ("base_url", "app", "app_key") if not feishu.get(key)]
            if missing:
                raise ValueError(f"Missing Feishu configuration: {', '.join(missing)}")

        self.config = loaded
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def get(self, key: str, default: Any = None) -> Any:
        self._ensure_loaded()
        value: Any = self.config
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def set(self, key: str, value: Any) -> None:
        self._ensure_loaded()
        target = self.config
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value

    def resolve_path(self, key: str) -> Path | None:
        value = self.get(key)
        if not value:
            return None
        path = Path(str(value)).expanduser()
        return path if path.is_absolute() else self.path.parent / path

    @property
    def app_root_path(self) -> Path:
        return APP_ROOT_PATH

    @property
    def app_logo_path(self) -> Path:
        logo = "gt_logo.png" if self.get("application.mode", "dev") == "gt" else "logo.png"
        return APP_ROOT_PATH / "static" / "images" / logo

    def get_sqlalchemy_database_url(self) -> str:
        prefix = "database.postgres"
        user = quote_plus(str(self.get(f"{prefix}.user", "")))
        password = quote_plus(str(self.get(f"{prefix}.password", "")))
        host = self.get(f"{prefix}.host", "")
        port = self.get(f"{prefix}.port", 5432)
        database = self.get(f"{prefix}.name", "")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    def get_quest_db_url(self) -> str:
        prefix = "database.questdb"
        user = quote_plus(str(self.get(f"{prefix}.user", "")))
        password = quote_plus(str(self.get(f"{prefix}.password", "")))
        host = self.get(f"{prefix}.host", "")
        port = self.get(f"{prefix}.port", 8812)
        return f"questdb://{user}:{password}@{host}:{port}/qdb?timezone=UTC"


base_config = Config()
