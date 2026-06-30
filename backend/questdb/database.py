# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from appConfig import base_config

url = base_config.get_quest_db_url()
print(f"Check Quest DB : {url}")
questdb_engine = create_engine(url,
                               pool_size=1024,
                               max_overflow=0,
                               pool_timeout=60,
                               pool_recycle=300,
                               pool_pre_ping=True)
QuestDBSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=questdb_engine)
QuestDBBase = declarative_base()
