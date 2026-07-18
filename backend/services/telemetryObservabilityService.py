# -*- coding: utf-8 -*-
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID, uuid4

from requests import exceptions as requests_exceptions
from sqlalchemy.exc import SQLAlchemyError

from crud import telemetryCollectionRunCrud


COMPONENTS = ("capacity", "vendor_events", "performance")
FRESHNESS_THRESHOLDS_SECONDS = {
    "capacity": 150,
    "vendor_events": 150,
    "performance": 630,
}
ERROR_CODES = ("vendor_auth", "vendor_timeout", "postgres", "questdb", "unknown")


@dataclass(frozen=True)
class TelemetryFreshness:
    status: str
    age_seconds: float | None
    data_state: str | None
    last_success_at: datetime | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def safe_trace_id(value: object | None) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return str(uuid4())


def task_execution_context(task) -> dict[str, object]:
    request = getattr(task, "request", None)
    headers = getattr(request, "headers", None) or {}
    trace_header = (
        headers.get("trace_id")
        or headers.get("trace-id")
        or headers.get("x-trace-id")
    )
    retries = getattr(request, "retries", 0) or 0
    return {
        "task_id": str(getattr(request, "id", None) or uuid4()),
        "attempt": int(retries) + 1,
        "trace_id": safe_trace_id(trace_header),
    }


def classify_error_code(error: Exception, *, phase: str) -> str:
    error_phase = getattr(error, "telemetry_phase", None)
    if error_phase in {"postgres", "questdb"}:
        return error_phase
    if phase in {"postgres", "questdb"}:
        return phase
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None) or getattr(error, "status", None)
    if status_code in {401, 403}:
        return "vendor_auth"
    if isinstance(error, (TimeoutError, requests_exceptions.Timeout)):
        return "vendor_timeout"
    if isinstance(error, SQLAlchemyError):
        return "postgres" if phase != "questdb" else "questdb"
    return "unknown"


def telemetry_freshness(
    component: str,
    last_success_at: datetime | None,
    *,
    now: datetime | None = None,
    data_state: str | None = None,
) -> TelemetryFreshness:
    if last_success_at is None:
        return TelemetryFreshness("unknown", None, None, None)
    collected_at = normalize_utc(last_success_at)
    current_time = normalize_utc(now or utc_now())
    age_seconds = max(0.0, (current_time - collected_at).total_seconds())
    threshold = FRESHNESS_THRESHOLDS_SECONDS[component]
    return TelemetryFreshness(
        "fresh" if age_seconds <= threshold else "stale",
        age_seconds,
        data_state,
        collected_at,
    )


def _session_write(session_factory: Callable, operation):
    db = session_factory()
    try:
        result = operation(db)
        db.commit()
        if hasattr(result, "id"):
            db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def start_collection_run(
    session_factory: Callable,
    *,
    task_id: str,
    attempt: int,
    scope_type: str,
    scope_key: str,
    storage_cluster_id: int | None,
    component: str,
    trace_id: str,
    started_at: datetime | None = None,
):
    return _session_write(
        session_factory,
        lambda db: telemetryCollectionRunCrud.create_collection_run(
            db,
            task_id=task_id,
            attempt=attempt,
            scope_type=scope_type,
            scope_key=scope_key,
            storage_cluster_id=storage_cluster_id,
            component=component,
            trace_id=safe_trace_id(trace_id),
            started_at=normalize_utc(started_at or utc_now()),
        ),
    )


def complete_collection_run(
    session_factory: Callable,
    run_id: UUID,
    *,
    outcome: str,
    data_state: str | None = None,
    records_written: int | None = None,
    error_code: str | None = None,
    finished_at: datetime | None = None,
):
    def operation(db):
        run = telemetryCollectionRunCrud.get_collection_run(db, run_id)
        if run is None:
            raise LookupError("Telemetry collection run is unavailable")
        run.outcome = outcome
        run.finished_at = normalize_utc(finished_at or utc_now())
        if outcome == "success":
            run.data_state = data_state
            run.records_written = records_written
            run.error_code = None
        elif outcome == "failed":
            if error_code not in ERROR_CODES:
                raise ValueError("failed telemetry runs require a classified error code")
            # Review fix: retain the classified failure reason in the telemetry ledger.
            run.data_state = None
            run.records_written = None
            run.error_code = error_code
        else:
            run.data_state = None
            run.records_written = None
            run.error_code = None
        return run

    return _session_write(session_factory, operation)


def safe_start_collection_run(session_factory: Callable, logger, **values):
    try:
        return start_collection_run(session_factory, **values)
    except Exception:
        logger.warning("Unable to persist telemetry collection start state")
        return None


def safe_complete_collection_run(session_factory: Callable, logger, run_id, **values) -> None:
    if run_id is None:
        return
    try:
        complete_collection_run(session_factory, run_id, **values)
    except Exception:
        logger.warning("Unable to persist telemetry collection completion state")


def record_scheduler_skip(
    session_factory: Callable,
    *,
    task_id: str,
    attempt: int,
    component: str,
    trace_id: str,
):
    run = start_collection_run(
        session_factory,
        task_id=task_id,
        attempt=attempt,
        scope_type="scheduler",
        scope_key="scheduler",
        storage_cluster_id=None,
        component=component,
        trace_id=trace_id,
    )
    return complete_collection_run(session_factory, run.id, outcome="skipped")


def safe_record_scheduler_skip(session_factory: Callable, logger, **values) -> None:
    try:
        record_scheduler_skip(session_factory, **values)
    except Exception:
        logger.warning("Unable to persist telemetry scheduler skip state")


def successful_data_state(records_written: int, *, unsupported: bool = False) -> str:
    if unsupported:
        return "unsupported"
    return "data" if records_written > 0 else "empty"


def list_collection_runs(db, **filters):
    return telemetryCollectionRunCrud.list_collection_runs(db, **filters)


def purge_expired_collection_runs(
    session_factory: Callable,
    *,
    cutoff: datetime,
    batch_size: int = 1000,
) -> int:
    return _session_write(
        session_factory,
        lambda db: telemetryCollectionRunCrud.purge_collection_runs_before(
            db,
            normalize_utc(cutoff),
            batch_size=batch_size,
        ),
    )


def is_explicitly_unsupported(error: Exception) -> bool:
    return isinstance(error, ValueError) and str(error).startswith("Unsupported storage type:")
