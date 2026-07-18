# -*- coding: utf-8 -*-
"""Read-only workload-to-storage correlation contracts.

Production Slurm, LSF and EDA connectors deliberately do not live here: their
API, authentication and field contracts are customer-specific.  Adapters pass
only an execution window and already-resolved AssetRef into this module.  Raw
job identifiers, paths, environments and logs are discarded before any
evidence is returned or persisted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal

from services.forecastIncidentService import AssetRef


SchedulerName = Literal["slurm", "lsf", "eda"]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("workload timestamps must include a timezone")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class WorkloadRun:
    """Transient normalized input from a customer-authorized read-only adapter."""

    scheduler: SchedulerName
    project_id: int | None
    hostname: str
    started_at: datetime
    ended_at: datetime
    asset_ref: AssetRef
    # Mapping-only values must not be copied into output or database records.
    raw_path: str | None = None
    job_id: str | None = None
    environment: dict[str, str] | None = None
    log_excerpt: str | None = None


class WorkloadStorageAdapter(ABC):
    """Safe boundary for customer-specific, read-only scheduler adapters."""

    scheduler: SchedulerName

    @abstractmethod
    def read_runs(self, *, starts_at: datetime, ends_at: datetime) -> Iterable[WorkloadRun]:
        """Return only authorized runs with a resolved AssetRef.

        Implementations must resolve storage paths locally and must not return
        a raw path, environment or log to persistence or an AI model.
        """


class FixtureWorkloadStorageAdapter(WorkloadStorageAdapter):
    """Fixture-only adapter for Slurm, LSF and EDA replay tests."""

    def __init__(self, scheduler: SchedulerName, runs: Iterable[WorkloadRun]):
        self.scheduler = scheduler
        self._runs = tuple(runs)

    def read_runs(self, *, starts_at: datetime, ends_at: datetime) -> Iterable[WorkloadRun]:
        starts_at, ends_at = _utc(starts_at), _utc(ends_at)
        return tuple(
            item
            for item in self._runs
            if item.scheduler == self.scheduler
            and _utc(item.started_at) < ends_at
            and _utc(item.ended_at) > starts_at
        )


def _window_start(value: datetime) -> datetime:
    value = _utc(value)
    return value.replace(minute=value.minute - value.minute % 5, second=0, microsecond=0)


def aggregate_workload_evidence(runs: Iterable[WorkloadRun]) -> list[dict]:
    """Aggregate active work by scheduler/project/host/asset and five-minute slot.

    The returned dictionaries are deliberately the only persistable form.  No
    job ID, raw path, environment or scheduler log is represented.
    """
    counts: dict[tuple, int] = {}
    for run in runs:
        started_at, ended_at = _utc(run.started_at), _utc(run.ended_at)
        if ended_at <= started_at:
            raise ValueError("workload end must follow start")
        slot = _window_start(started_at)
        while slot < ended_at:
            key = (
                run.scheduler,
                run.project_id,
                run.hostname,
                run.asset_ref.model_dump_json(),
                slot,
            )
            counts[key] = counts.get(key, 0) + 1
            slot += timedelta(minutes=5)

    return [
        {
            "scheduler": scheduler,
            "project_id": project_id,
            "hostname": hostname,
            "asset_ref": AssetRef.model_validate_json(asset_ref_json).model_dump(),
            "window_start": window_start,
            "active_job_count": active_job_count,
        }
        for (scheduler, project_id, hostname, asset_ref_json, window_start), active_job_count in sorted(
            counts.items(), key=lambda item: item[0][-1]
        )
    ]
