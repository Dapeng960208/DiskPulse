# -*- coding: utf-8 -*-
from urllib.parse import urlsplit

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from appConfig import base_config

url = base_config.get_quest_db_url()
_quest_url = urlsplit(url)
print(f"Check Quest DB : {_quest_url.hostname}:{_quest_url.port or ''}{_quest_url.path}")
questdb_engine = create_engine(url,
                               pool_size=base_config.get("database.questdb.pool_size", 20),
                               max_overflow=base_config.get("database.questdb.max_overflow", 0),
                               pool_timeout=base_config.get("database.questdb.pool_timeout", 60),
                               pool_recycle=base_config.get("database.questdb.pool_recycle", 300),
                               pool_pre_ping=True)
QuestDBSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=questdb_engine)
QuestDBBase = declarative_base()
