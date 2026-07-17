# -*- coding: utf-8 -*-
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from appConfig import base_config

SQLALCHEMY_DATABASE_URL = base_config.get_sqlalchemy_database_url()
_db_url = urlsplit(SQLALCHEMY_DATABASE_URL)
print(f"check db:{_db_url.hostname}:{_db_url.port or ''}/{_db_url.path.lstrip('/')}")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=base_config.get("database.postgres.pool_size", 20),
    max_overflow=base_config.get("database.postgres.max_overflow", 10),
    pool_timeout=base_config.get("database.postgres.pool_timeout", 10),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
