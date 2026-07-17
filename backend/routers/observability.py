# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST

from schemas.telemetryObservabilitySchema import HealthStatus
from services import observabilityService


router = APIRouter(prefix="/v1", tags=["observability"])


@router.get("/healthz", response_model=HealthStatus)
def healthz() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/readyz", response_model=HealthStatus)
def readyz() -> Response | HealthStatus:
    dependencies = observabilityService.check_dependencies()
    observabilityService.update_dependency_metrics(dependencies)
    if not dependencies["postgres"] or not dependencies["redis"]:
        return Response(
            content=HealthStatus(status="not_ready").model_dump_json(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )
    if not dependencies["questdb"]:
        return HealthStatus(status="degraded")
    return HealthStatus(status="ready")


@router.get("/metrics", include_in_schema=False)
def metrics(
    metrics_token: Annotated[str | None, Header(alias="X-Metrics-Token")] = None,
) -> Response:
    if not observabilityService.metrics_token_is_valid(metrics_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="metrics access denied")
    return Response(
        content=observabilityService.render_metrics(),
        media_type=CONTENT_TYPE_LATEST,
    )
