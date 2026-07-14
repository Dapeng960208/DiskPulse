# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DisconnectionError

import models
from appConfig import base_config
from database import Base, SessionLocal, engine
from dependencies import require_authenticated_request
from questdb.migrate import upgrade as upgrade_questdb
from routers import (
    aggregate,
    config,
    group,
    large_files,
    project_storage_environment,
    projects,
    qtrees,
    storage_alerts,
    storage_back_up_records,
    storage_cluster,
    storage_usage,
    users,
    volumes,
)

if base_config.get("database.create_tables", False):
    Base.metadata.create_all(bind=engine)
    upgrade_questdb()

app = FastAPI(
    title="DiskPulse API",
    description="DiskPulse storage monitoring API",
    summary="DiskPulse API",
    version="1.0.0",
    contact={"name": "DiskPulse Maintainers"},
)

storage_router = APIRouter(prefix="/storage-pulse/api", dependencies=[Depends(require_authenticated_request)])
storage_router.include_router(users.router)
storage_router.include_router(projects.router)
storage_router.include_router(project_storage_environment.router)
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

cors_origins = base_config.get("application.cors_origins", [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
    except Exception:
        request.state.db.rollback()
        raise
    finally:
        request.state.db.close()
    return response
