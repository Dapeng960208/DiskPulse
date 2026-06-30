# -*- coding: utf-8 -*-
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from appConfig import base_config

SQLALCHEMY_DATABASE_URL = base_config.get_sqlalchemy_database_url()
print(f"check db:{SQLALCHEMY_DATABASE_URL}")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=200,
    max_overflow=20,
    pool_timeout=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
