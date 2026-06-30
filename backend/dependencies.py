# -*- coding: utf-8 -*-
from fastapi import Depends, FastAPI, Request, Response
from database import SessionLocal
from questdb.database import QuestDBSessionLocal, questdb_engine


class DBSession:
    def __enter__(self):
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()


def get_db(request: Request):
    return request.state.db


class QuestDBSession:
    def __init__(self, config=None):
        self.config = config

    def __enter__(self):
        self.quest_db = QuestDBSessionLocal()
        return self.quest_db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quest_db.close()


def get_questdb_session():
    return QuestDBSessionLocal()


def get_questdb_engine():
    return questdb_engine
