# -*- coding: utf-8 -*-
# config.py

import os
from dotenv import load_dotenv, dotenv_values
from typing import Any, Optional
from urllib.parse import quote_plus

current_file_path = os.path.realpath(__file__)
app_root_path = os.path.dirname(current_file_path)

class ConfigSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigSingleton, cls).__new__(cls)
        return cls._instance

    def __init__(self, model: Optional[str] = None):
        if not hasattr(self, 'config_loaded'):
            self.config_loaded = True
            self.config = {}
            self.load_environment_variables(model)

    def load_environment_variables(self, model: Optional[str] = None):
        model = model or os.environ.get('MODEL', 'dev').lower()
        os.environ['MODEL'] = model
        self.config['MODEL'] = model
        env_file_path = self.get_env_file_path(model=model)
        load_dotenv(env_file_path, override=True)

        self.populate_config(env_file_path)

    @staticmethod
    def get_env_file_path(model: Optional[str] = None) -> str:
        paths = {
            'dev': "development.env",
            'test': "test.env",
        }
        return os.path.join(app_root_path,paths.get(model))

    def populate_config(self, env_file_path: str):
        env_vars = dotenv_values(env_file_path)

        for key, value in env_vars.items():
            self.config[key] = value

        self.config['SQL_DATABASE_URL'] = (
            f"postgresql+psycopg2://{self.config.get('PG_USER', '')}:"
            f"{quote_plus(self.config.get('PG_PASSWORD', ''))}@{self.config.get('PG_IP', '')}:"
            f"{self.config.get('PG_PORT', '5432')}/{self.config.get('DATABASE_NAME', '')}"
        )

        self.config['QUEST_DATABASE_URL'] = (
            f"questdb://{self.config['QUEST_USER']}:"
            f"{quote_plus(self.config['QUEST_PASSWORD'])}@{self.config['QUEST_IP']}:"
            f"{self.config['QUEST_PORT']}/qdb?timezone=UTC"
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        os.environ[key] = str(value)

    def get_sqlalchemy_database_url(self) -> str:
        return self.get('SQL_DATABASE_URL')

    def get_quest_db_url(self) -> str:
        return self.get('QUEST_DATABASE_URL')

    def get_info(self):
        return [(key, value) for key, value in self.config.items()]


base_config = ConfigSingleton(model=os.environ.get('MODEL', 'dev'))
base_config.set('APP_ROOT_PATH', app_root_path)

app_logo_path = 'gt_logo.png' if os.environ['MODEL'] == 'gt' else 'logo.png'
base_config.set('APP_LOGO_PATH', os.path.join(app_root_path, 'static', 'images', app_logo_path))
