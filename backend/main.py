# -*- coding: utf-8 -*-
import os

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DisconnectionError

import models
from database import Base, SessionLocal, engine
from questdb.database import QuestDBBase, questdb_engine
from routers import (
    aggregate,
    config,
    group,
    large_files,
    projects,
    qtrees,
    storage_alerts,
    storage_back_up_records,
    storage_cluster,
    storage_usage,
    users,
    volumes,
)

if os.getenv("DISKPULSE_CREATE_TABLES", "false").lower() == "true":
    Base.metadata.create_all(bind=engine)
    QuestDBBase.metadata.create_all(bind=questdb_engine)

app = FastAPI(
    title="DiskPulse API",
    description="DiskPulse storage monitoring API",
    summary="DiskPulse API",
    version="1.0.0",
    contact={"name": "guojianpeng"},
)

storage_router = APIRouter(prefix="/storage-pulse/api")
storage_router.include_router(users.router)
storage_router.include_router(projects.router)
storage_router.include_router(config.router)
storage_router.include_router(group.router)
storage_router.include_router(storage_cluster.router)
storage_router.include_router(aggregate.router)
storage_router.include_router(volumes.router)
storage_router.include_router(qtrees.router)
storage_router.include_router(storage_usage.router)
storage_router.include_router(storage_alerts.router)
storage_router.include_router(storage_back_up_records.router)
storage_router.include_router(large_files.router)
app.include_router(storage_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    request.state.db = SessionLocal()
    try:
        try:
            request.scope["path"] = request.scope["path"].replace("//", "/")
            response = await call_next(request)
        except DisconnectionError:
            request.state.db.close()
            request.state.db = SessionLocal()
            response = await call_next(request)
    finally:
        request.state.db.close()
    return response
