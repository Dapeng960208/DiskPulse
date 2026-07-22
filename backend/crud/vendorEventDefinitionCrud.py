# -*- coding: utf-8 -*-
from collections.abc import Iterable

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.orm import Session

from models import StorageAlerts, VendorEventDefinition


VENDOR_STORAGE_TYPES = ("netapp", "isilon")
_DEFINITION_KEY_BATCH_SIZE = 400


def create_definition(
    db: Session,
    *,
    storage_type: str,
    event_code: str,
    association_type: str,
    title_zh: str,
    description_zh: str,
    official_reference_url: str | None = None,
    default_severity: str | None = None,
    version_scope: str | None = None,
    review_status: str = "pending",
    recommended_solution_zh: str | None = None,
    is_active: bool = True,
) -> VendorEventDefinition:
    definition = VendorEventDefinition(
        storage_type=storage_type,
        event_code=event_code,
        association_type=association_type,
        title_zh=title_zh,
        description_zh=description_zh,
        official_reference_url=official_reference_url,
        default_severity=default_severity,
        version_scope=version_scope,
        review_status=review_status,
        recommended_solution_zh=recommended_solution_zh,
        is_active=is_active,
    )
    db.add(definition)
    db.flush()
    return definition


def get_definition(
    db: Session,
    storage_type: str,
    event_code: str,
) -> VendorEventDefinition | None:
    return db.scalar(
        select(VendorEventDefinition).where(
            VendorEventDefinition.storage_type == storage_type,
            VendorEventDefinition.event_code == event_code,
        )
    )


def get_definition_map(
    db: Session,
    keys: Iterable[tuple[str, str]],
) -> dict[tuple[str, str], VendorEventDefinition]:
    normalized_keys = sorted(
        {
            (str(storage_type).strip().lower(), str(event_code).strip())
            for storage_type, event_code in keys
            if str(storage_type).strip() and str(event_code).strip()
        }
    )
    if not normalized_keys:
        return {}
    definitions = []
    for offset in range(0, len(normalized_keys), _DEFINITION_KEY_BATCH_SIZE):
        batch = normalized_keys[offset : offset + _DEFINITION_KEY_BATCH_SIZE]
        definitions.extend(
            db.scalars(
                select(VendorEventDefinition).where(
                    tuple_(
                        VendorEventDefinition.storage_type,
                        VendorEventDefinition.event_code,
                    ).in_(batch)
                )
            )
        )
    return {
        (definition.storage_type, definition.event_code): definition
        for definition in definitions
    }


def get_definition_by_id(
    db: Session,
    definition_id: int,
) -> VendorEventDefinition | None:
    return db.get(VendorEventDefinition, definition_id)


def _apply_filters(
    statement,
    *,
    storage_type: str | None = None,
    association_type: str | None = None,
    keyword: str | None = None,
    review_status: str | None = None,
    active_only: bool = False,
):
    if storage_type is not None:
        statement = statement.where(
            VendorEventDefinition.storage_type == storage_type
        )
    if association_type is not None:
        statement = statement.where(
            VendorEventDefinition.association_type == association_type
        )
    if review_status is not None:
        statement = statement.where(
            VendorEventDefinition.review_status == review_status
        )
    if active_only:
        statement = statement.where(VendorEventDefinition.is_active.is_(True))
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                VendorEventDefinition.event_code.ilike(pattern),
                VendorEventDefinition.title_zh.ilike(pattern),
                VendorEventDefinition.description_zh.ilike(pattern),
            )
        )
    return statement


def list_definitions(
    db: Session,
    *,
    storage_type: str | None = None,
    association_type: str | None = None,
    keyword: str | None = None,
    review_status: str | None = None,
    active_only: bool = False,
    offset: int | None = None,
    limit: int | None = None,
) -> list[VendorEventDefinition]:
    statement = _apply_filters(
        select(VendorEventDefinition),
        storage_type=storage_type,
        association_type=association_type,
        keyword=keyword,
        review_status=review_status,
        active_only=active_only,
    ).order_by(
        VendorEventDefinition.storage_type,
        VendorEventDefinition.event_code,
        VendorEventDefinition.id,
    )
    if offset is not None:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def count_definitions(
    db: Session,
    *,
    storage_type: str | None = None,
    association_type: str | None = None,
    keyword: str | None = None,
    review_status: str | None = None,
    active_only: bool = False,
) -> int:
    statement = _apply_filters(
        select(func.count()).select_from(VendorEventDefinition),
        storage_type=storage_type,
        association_type=association_type,
        keyword=keyword,
        review_status=review_status,
        active_only=active_only,
    )
    return int(db.scalar(statement) or 0)


def update_definition(
    db: Session,
    definition_id: int,
    **values,
) -> VendorEventDefinition | None:
    definition = get_definition_by_id(db, definition_id)
    if definition is None:
        return None
    for key, value in values.items():
        setattr(definition, key, value)
    db.flush()
    return definition


def delete_definition(db: Session, definition_id: int) -> bool:
    definition = get_definition_by_id(db, definition_id)
    if definition is None:
        return False
    db.delete(definition)
    db.flush()
    return True


def list_observed_vendor_event_codes(db: Session) -> list[tuple[str, str]]:
    event_code = func.trim(
        StorageAlerts.related_info["event_code"].as_string()
    ).label("event_code")
    rows = db.execute(
        select(StorageAlerts.source, event_code)
        .where(
            StorageAlerts.source.in_(VENDOR_STORAGE_TYPES),
            StorageAlerts.related_info.is_not(None),
            event_code.is_not(None),
            event_code != "",
        )
        .distinct()
    )
    return sorted((str(storage_type), str(code)) for storage_type, code in rows)
