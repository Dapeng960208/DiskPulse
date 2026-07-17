# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from models import TelemetryCollectionRun


def create_collection_run(db: Session, **values) -> TelemetryCollectionRun:
    run = TelemetryCollectionRun(**values)
    db.add(run)
    db.flush()
    return run


def get_collection_run(db: Session, run_id: UUID) -> TelemetryCollectionRun | None:
    return db.get(TelemetryCollectionRun, run_id)


def list_collection_runs(
    db: Session,
    *,
    cluster_id: int | None = None,
    component: str | None = None,
    started_at_from: datetime | None = None,
    started_at_to: datetime | None = None,
    page: int,
    size: int,
) -> tuple[list[TelemetryCollectionRun], int]:
    statement = select(TelemetryCollectionRun)
    if cluster_id is not None:
        statement = statement.where(
            or_(
                TelemetryCollectionRun.storage_cluster_id == cluster_id,
                TelemetryCollectionRun.scope_key == str(cluster_id),
            )
        )
    if component is not None:
        statement = statement.where(TelemetryCollectionRun.component == component)
    if started_at_from is not None:
        statement = statement.where(TelemetryCollectionRun.started_at >= started_at_from)
    if started_at_to is not None:
        statement = statement.where(TelemetryCollectionRun.started_at <= started_at_to)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    runs = db.execute(
        statement.order_by(
            TelemetryCollectionRun.started_at.desc(),
            TelemetryCollectionRun.id.desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()
    return runs, total


def list_latest_success_runs(db: Session, active_cluster_ids: tuple[int, ...]) -> list[TelemetryCollectionRun]:
    if not active_cluster_ids:
        return []
    latest_success = (
        select(
            TelemetryCollectionRun.id.label("run_id"),
            func.row_number()
            .over(
                partition_by=(
                    TelemetryCollectionRun.component,
                    TelemetryCollectionRun.storage_cluster_id,
                ),
                order_by=(
                    TelemetryCollectionRun.finished_at.desc(),
                    TelemetryCollectionRun.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(
            TelemetryCollectionRun.storage_cluster_id.in_(active_cluster_ids),
            TelemetryCollectionRun.outcome == "success",
            TelemetryCollectionRun.finished_at.is_not(None),
        )
        .subquery()
    )
    return db.execute(
        select(TelemetryCollectionRun)
        .join(latest_success, TelemetryCollectionRun.id == latest_success.c.run_id)
        .where(latest_success.c.row_number == 1)
        .order_by(
            TelemetryCollectionRun.component,
            TelemetryCollectionRun.storage_cluster_id,
            TelemetryCollectionRun.finished_at.desc(),
            TelemetryCollectionRun.id.desc(),
        )
    ).scalars().all()


def purge_collection_runs_before(db: Session, cutoff: datetime, *, batch_size: int) -> int:
    run_ids = db.execute(
        select(TelemetryCollectionRun.id)
        .where(TelemetryCollectionRun.created_at < cutoff)
        .order_by(TelemetryCollectionRun.created_at)
        .limit(batch_size)
    ).scalars().all()
    if not run_ids:
        return 0
    result = db.execute(delete(TelemetryCollectionRun).where(TelemetryCollectionRun.id.in_(run_ids)))
    return result.rowcount or 0
