# -*- coding: utf-8 -*-
from sqlalchemy import select

from models import AIConfig, IncidentAiModelBinding, IncidentAiSettings, IncidentAiRun


def get_settings(db) -> IncidentAiSettings | None:
    return db.get(IncidentAiSettings, 1)


def get_or_create_settings(db) -> IncidentAiSettings:
    settings = get_settings(db)
    if settings is None:
        settings = IncidentAiSettings(id=1, enabled=False, iops_absolute_floor=10.0, iops_baseline_ratio=0.05)
        db.add(settings)
        db.flush()
    return settings


def list_models_by_ids(db, model_ids: list[int]) -> list[AIConfig]:
    if not model_ids:
        return []
    return list(db.scalars(select(AIConfig).where(AIConfig.id.in_(model_ids))))


def replace_model_bindings(db, *, settings: IncidentAiSettings, model_ids: list[int]) -> None:
    settings.model_bindings.clear()
    db.flush()
    for priority, model_id in enumerate(model_ids):
        settings.model_bindings.append(IncidentAiModelBinding(ai_model_id=model_id, priority=priority))
    db.flush()


def get_run_by_idempotency_key(db, key: str) -> IncidentAiRun | None:
    return db.scalar(select(IncidentAiRun).where(IncidentAiRun.idempotency_key == key))


def add_run(db, run: IncidentAiRun) -> IncidentAiRun:
    db.add(run)
    db.flush()
    return run
