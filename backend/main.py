# -*- coding: utf-8 -*-
import time

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DisconnectionError

from appConfig import base_config
from database import SessionLocal
from dependencies import require_authenticated_request
from middleware.correlation import CorrelationIdMiddleware
from middleware.operation_audit import OperationAuditMiddleware
from questdb.migrate import upgrade as upgrade_questdb
from routers import (
    aggregate,
    ai,
    ai_admin,
    audit_events,
    config,
    dashboard,
    forecast_incidents,
    group,
    group_tag,
    large_files,
    project_memberships,
    projects,
    qtrees,
    storage_alerts,
    storage_back_up_records,
    storage_cluster,
    storage_usage,
    telemetry,
    users,
    vendor_event_definitions,
    volumes,
    observability,
)
from services import observabilityService
from utils.security import validate_jwt_secret_key

def _validate_cors_origins(cors_origins: object, *, allow_credentials: bool) -> list[str]:
    if not isinstance(cors_origins, list) or not all(isinstance(origin, str) for origin in cors_origins):
        raise RuntimeError("application.cors_origins must be a list of origin strings")
    if allow_credentials and any(origin.strip() == "*" for origin in cors_origins):
        raise RuntimeError("application.cors_origins must not contain '*' when credentials are enabled")
    return cors_origins


def create_app() -> FastAPI:
    validate_jwt_secret_key()
    allow_credentials = True
    cors_origins = _validate_cors_origins(
        base_config.get("application.cors_origins", []),
        allow_credentials=allow_credentials,
    )
    if base_config.get("database.create_tables", False):
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
    storage_router.include_router(ai.router)
    storage_router.include_router(ai_admin.router)
    storage_router.include_router(audit_events.router)
    storage_router.include_router(projects.router)
    storage_router.include_router(project_memberships.router)
    storage_router.include_router(group_tag.router)
    storage_router.include_router(config.router)
    storage_router.include_router(dashboard.router)
    storage_router.include_router(group.router)
    storage_router.include_router(storage_cluster.router)
    storage_router.include_router(vendor_event_definitions.router)
    storage_router.include_router(aggregate.router)
    storage_router.include_router(volumes.router)
    storage_router.include_router(qtrees.router)
    storage_router.include_router(storage_usage.router)
    storage_router.include_router(storage_alerts.router)
    # These routes remain part of the frontend and external API contract; route
    # usage cannot be inferred only from imports inside the backend package.
    storage_router.include_router(storage_back_up_records.router)
    storage_router.include_router(large_files.router)
    app.include_router(storage_router)
    app.include_router(observability.router, prefix="/storage-pulse/api")
    v1_authenticated_router = APIRouter(
        prefix="/storage-pulse/api",
        dependencies=[Depends(require_authenticated_request)],
    )
    v1_authenticated_router.include_router(telemetry.router)
    v1_authenticated_router.include_router(forecast_incidents.router)
    app.include_router(v1_authenticated_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OperationAuditMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    @app.middleware("http")
    async def db_session_middleware(request: Request, call_next):
        request.scope["path"] = request.scope["path"].replace("//", "/")
        if request.url.path in {
            "/storage-pulse/api/v1/healthz",
            "/storage-pulse/api/v1/readyz",
            "/storage-pulse/api/v1/metrics",
        }:
            started = time.perf_counter()
            response = await call_next(request)
            observabilityService.record_http_request(
                request,
                response,
                time.perf_counter() - started,
            )
            return response

        started = time.perf_counter()
        response = Response("Internal server error", status_code=500)
        request.state.db = SessionLocal()
        try:
            try:
                response = await call_next(request)
            except DisconnectionError:
                request.state.db.close()
                request.state.db = SessionLocal()
                response = await call_next(request)
        finally:
            request.state.db.close()
            observabilityService.record_http_request(
                request,
                response,
                time.perf_counter() - started,
            )
        return response

    return app


app = create_app()
