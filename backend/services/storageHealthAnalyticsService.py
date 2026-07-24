# -*- coding: utf-8 -*-
import csv
import io
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from schemas.capacitySchema import format_capacity_fields

from appConfig import base_config
from crud import storageHealthAnalyticsCrud, vendorEventDefinitionCrud
from models import Volume
from services import vendorEventDefinitionService
from utils.datetime_utils import format_for_user_time_zone
from utils.pdf.pdfReporter import PDFReportGenerator


SEVERITIES = ("critical", "error", "warning", "info")
SEVERITY_MAP = {
    "emergency": "critical",
    "alert": "critical",
    "critical": "critical",
    "high": "critical",
    "error": "error",
    "warning": "warning",
    "warn": "warning",
    "medium": "warning",
    "notice": "warning",
    "informational": "info",
    "information": "info",
    "info": "info",
    "debug": "info",
    "low": "info",
}


def normalize_severity(value: Any) -> str:
    return SEVERITY_MAP.get(str(value or "info").lower(), "info")


def validate_time_range(start_time: datetime, end_time: datetime) -> None:
    if (
        start_time.tzinfo is None
        or start_time.utcoffset() is None
        or end_time.tzinfo is None
        or end_time.utcoffset() is None
    ):
        raise ValueError("start_time and end_time must be timezone-aware")
    if start_time >= end_time:
        raise ValueError("start_time must be before end_time")
    if end_time - start_time > timedelta(days=180):
        raise ValueError("time range cannot exceed 180 days")


def summarize_capacity(
    points: list[dict],
    start_used: float | None = None,
    end_used: float | None = None,
) -> dict:
    ordered = sorted(points, key=lambda point: point["updated_at"])
    if not ordered:
        return {
            "start_used": None,
            "end_used": None,
            "change": None,
            "change_percent": None,
            "points": [],
        }
    start_used = ordered[0]["used"] if start_used is None else start_used
    end_used = ordered[-1]["used"] if end_used is None else end_used
    change = end_used - start_used
    return {
        "start_used": start_used,
        "end_used": end_used,
        "change": change,
        "change_percent": None if start_used == 0 else round(change * 100 / start_used, 2),
        "points": ordered,
    }


def summarize_severities(alerts: list[dict]) -> dict:
    counts = dict.fromkeys(SEVERITIES, 0)
    sources: dict[str, dict[str, int]] = {}
    for alert in alerts:
        source = str(alert.get("source") or "diskpulse").lower()
        severity = normalize_severity(alert.get("severity"))
        counts[severity] += 1
        sources.setdefault(source, dict.fromkeys(SEVERITIES, 0))[severity] += 1
    return {"counts": counts, "total": sum(counts.values()), "sources": sources}


def rank_top_latency(rows: list[dict], limit: int = 10) -> list[dict]:
    return sorted(rows, key=lambda row: row["p95_latency"], reverse=True)[:limit]


def group_repeated_faults(events: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[datetime]] = defaultdict(list)
    for event in events:
        source = str(event.get("source") or "").lower()
        fingerprint = event.get("fingerprint")
        if source not in {"netapp", "isilon"} or not fingerprint:
            continue
        grouped[(source, fingerprint)].append(event["occurred_at"])
    repeated = [
        {
            "source": source,
            "fingerprint": fingerprint,
            "count": len(occurred_at),
            "first_occurred_at": min(occurred_at),
            "last_occurred_at": max(occurred_at),
        }
        for (source, fingerprint), occurred_at in grouped.items()
        if len(occurred_at) >= 2
    ]
    return sorted(repeated, key=lambda row: (row["count"], row["last_occurred_at"]), reverse=True)


def get_capacity_change(
    db: Session, storage_cluster_id: int, start_time: datetime, end_time: datetime
) -> dict:
    start_used, end_used = storageHealthAnalyticsCrud.get_capacity_boundaries(
        db, storage_cluster_id, start_time, end_time
    )
    result = summarize_capacity(
        storageHealthAnalyticsCrud.get_capacity_points(
            db, storage_cluster_id, start_time, end_time
        ),
        start_used=start_used,
        end_used=end_used,
    )
    result["capacity"] = format_capacity_fields(
        {key: result.get(key) for key in ("start_used", "end_used", "change")}
    )
    result["data"] = [
        {
            **point,
            "used": round(float(point["used"]) / 1024, 4),
            "capacity": format_capacity_fields({"used": point.get("used")}),
        }
        for point in result.pop("points")
    ]
    for key in ("start_used", "end_used", "change"):
        if result[key] is not None:
            result[key] = round(float(result[key]) / 1024, 4)
    result["data_unit"] = "TB"
    return result


def get_error_severity(
    db: Session, storage_cluster_id: int, start_time: datetime, end_time: datetime
) -> dict:
    return summarize_severities(
        storageHealthAnalyticsCrud.get_alert_severities(
            db, storage_cluster_id, start_time, end_time
        )
    )


def get_top_latency(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
    limit: int = 10,
    object_type: str | None = None,
) -> dict:
    volume_identities = None
    query_limit = limit
    if object_type == "volume":
        volume_identities = set(
            db.execute(
                select(Volume.performance_object_id).where(
                    Volume.storage_cluster_id == storage_cluster_id,
                    Volume.performance_object_id.is_not(None),
                )
            ).scalars()
        )
        query_limit = max(limit, len(volume_identities))
    rows = storageHealthAnalyticsCrud.get_top_latency_rows(
        db,
        storage_cluster_id,
        start_time,
        end_time,
        query_limit,
        object_type,
        volume_identities,
    )
    if volume_identities is not None:
        rows = [row for row in rows if row.get("object_id") in volume_identities]
    supported = bool(rows) or storageHealthAnalyticsCrud.has_performance_metrics(
        db, storage_cluster_id
    )
    return {"supported": supported, "data": rank_top_latency(rows, limit)}


def get_system_events(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
    keyword: str | None = None,
    severity: str | None = None,
    fingerprint: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = {
        "keyword": keyword,
        "severity": severity,
        "page": page,
        "page_size": page_size,
    }
    if fingerprint is not None:
        query["fingerprint"] = fingerprint
    total, rows = storageHealthAnalyticsCrud.get_system_event_rows(
        db,
        storage_cluster_id,
        start_time,
        end_time,
        include_identity=True,
        **query,
    )
    definition_map = _definition_map_for_events(db, rows)
    return {
        "data": [
            _enrich_vendor_event(db, row, definition_map=definition_map)
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_repeated_faults(
    db: Session, storage_cluster_id: int, start_time: datetime, end_time: datetime
) -> dict:
    repeated_rows = storageHealthAnalyticsCrud.get_repeated_fault_rows(
        db, storage_cluster_id, start_time, end_time
    )
    samples = storageHealthAnalyticsCrud.get_system_events_by_ids(
        db,
        storage_cluster_id,
        (row["sample_event_id"] for row in repeated_rows),
    )
    definition_map = _definition_map_for_events(db, samples.values())
    result = []
    for row in repeated_rows:
        sample = samples.get(row["sample_event_id"])
        if sample is None:
            continue
        enriched = _enrich_vendor_event(
            db,
            sample,
            definition_map=definition_map,
        )
        if enriched["association_type"] != "fault_log":
            continue
        result.append(
            {
                **row,
                **_semantics_fields(enriched),
                "log_excerpt": enriched.get("description"),
            }
        )
    return {"data": result}


def _definition_field(definition, name: str):
    if isinstance(definition, dict):
        return definition.get(name)
    return getattr(definition, name, None)


def _semantics_fields(event: dict) -> dict:
    return {
        name: event.get(name)
        for name in (
            "event_code",
            "association_type",
            "association_type_label",
            "title_zh",
            "description_zh",
            "official_reference_url",
            "review_status",
        )
    }


def _vendor_event_key(row: dict) -> tuple[str, str] | None:
    storage_type = str(row.get("source") or "").strip().lower()
    event_code_value = row.get("event_code")
    event_code = (
        event_code_value.strip() if isinstance(event_code_value, str) else ""
    )
    if storage_type not in {"netapp", "isilon"} or not event_code:
        return None
    return storage_type, event_code


def _definition_map_for_events(db: Session, rows) -> dict:
    keys = {
        key
        for row in rows
        if (key := _vendor_event_key(row)) is not None
    }
    return vendorEventDefinitionCrud.get_definition_map(db, keys)


def _definition_for_event(
    db: Session,
    row: dict,
    definition_map: dict | None,
):
    key = _vendor_event_key(row)
    if definition_map is None:
        return vendorEventDefinitionService.resolve_definition(
            db,
            row.get("source"),
            row.get("event_code"),
        )
    definition = definition_map.get(key) if key is not None else None
    if (
        definition is not None
        and definition.is_active
        and definition.review_status == "reviewed"
    ):
        return vendorEventDefinitionService.serialize_definition(definition)
    return vendorEventDefinitionService.resolve_definition(
        db,
        None,
        key[1] if key is not None else None,
    )


def _enrich_vendor_event(
    db: Session,
    row: dict,
    *,
    definition_map: dict | None = None,
) -> dict:
    if row.get("source") not in {"netapp", "isilon"}:
        return dict(row)
    definition = _definition_for_event(db, row, definition_map)
    enriched = {
        **row,
        "association_type": _definition_field(definition, "association_type"),
        "association_type_label": _definition_field(definition, "association_type_label"),
        "title_zh": _definition_field(definition, "title_zh"),
        "description_zh": _definition_field(definition, "description_zh"),
        "official_reference_url": _definition_field(
            definition, "official_reference_url"
        ),
        "review_status": _definition_field(definition, "review_status"),
        "recommended_solution_zh": _definition_field(
            definition, "recommended_solution_zh"
        ),
    }
    enriched.pop("external_event_id", None)
    return enriched


def get_system_event_detail(
    db: Session, storage_cluster_id: int, event_id: int
) -> dict | None:
    row = storageHealthAnalyticsCrud.get_system_event_by_id(
        db, storage_cluster_id, event_id
    )
    return None if row is None else _enrich_vendor_event(db, row)


def _report_data(
    db: Session, storage_cluster_id: int, start_time: datetime, end_time: datetime
) -> dict[str, dict]:
    return {
        "capacity": get_capacity_change(db, storage_cluster_id, start_time, end_time),
        "severity": get_error_severity(db, storage_cluster_id, start_time, end_time),
        "latency": get_top_latency(db, storage_cluster_id, start_time, end_time),
        "faults": get_repeated_faults(db, storage_cluster_id, start_time, end_time),
    }


def _section_rows(section: str, report: dict[str, dict]) -> list[dict]:
    if section == "capacity":
        summary = {
            key: report[section].get(key)
            for key in ("start_used", "end_used", "change", "change_percent")
        }
        summary["data_unit"] = report[section].get("data_unit")
        points = report[section]["data"]
        return [{**point, **summary} for point in points] or [summary]
    if section == "severity":
        return [
            {
                "severity": severity,
                "count": count,
                "total": report[section]["total"],
                "sources": report[section]["sources"],
            }
            for severity, count in report[section]["counts"].items()
        ]
    return report[section]["data"]


def _escape_formula(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _safe_rows(rows: list[dict]) -> list[dict]:
    return [
        {key: _escape_formula(value) for key, value in row.items()}
        for row in rows
    ]


def _format_for_export(value, time_zone: str | None):
    if isinstance(value, datetime):
        return format_for_user_time_zone(value, time_zone)
    if isinstance(value, dict):
        return {key: _format_for_export(item, time_zone) for key, item in value.items()}
    if isinstance(value, list):
        return [_format_for_export(item, time_zone) for item in value]
    if isinstance(value, tuple):
        return tuple(_format_for_export(item, time_zone) for item in value)
    return value


def _presentation_rows(rows: list[dict], time_zone: str | None) -> list[dict]:
    return [_format_for_export(row, time_zone) for row in rows]


def _csv_bytes(rows: list[dict]) -> bytes:
    rows = _safe_rows(rows)
    output = io.StringIO(newline="")
    fieldnames = list(rows[0]) if rows else ["data"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _excel_bytes(
    sections: list[str], report: dict[str, dict], time_zone: str | None = None
) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for section in sections:
            rows = _presentation_rows(_section_rows(section, report), time_zone)
            pd.DataFrame(_safe_rows(rows)).to_excel(
                writer, sheet_name=section, index=False
            )
    return output.getvalue()


def _pdf_bytes(
    sections: list[str], report: dict[str, dict], time_zone: str | None = None
) -> bytes:
    logo_path = base_config.app_logo_path
    generator = PDFReportGenerator(
        company_name=base_config.get("application.company_name") or "DiskPulse",
        logo_path=str(logo_path) if logo_path.exists() else None,
        title="存储健康分析报告",
        app="DiskPulse",
        time_zone=time_zone,
    )
    generator.create_cover_page()
    for section in sections:
        rows = _presentation_rows(_section_rows(section, report), time_zone)
        headers = list(rows[0]) if rows else ["data"]
        values = [[row.get(header) for header in headers] for row in rows]
        generator.add_table([headers, *values], section)
    output = generator.generate_pdf()
    output.seek(0)
    return output.read()


def export_storage_health(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
    export_format: str,
    section: str,
    *,
    time_zone: str | None,
) -> tuple[bytes, str, str]:
    report = _report_data(db, storage_cluster_id, start_time, end_time)
    sections = list(report) if section == "all" else [section]
    if export_format == "csv" and section != "all":
        return (
            _csv_bytes(_presentation_rows(_section_rows(section, report), time_zone)),
            "text/csv",
            f"storage-health-{section}.csv",
        )
    if export_format == "csv":
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in sections:
                archive.writestr(
                    f"storage-health-{name}.csv",
                    _csv_bytes(
                        _presentation_rows(_section_rows(name, report), time_zone)
                    ),
                )
        return output.getvalue(), "application/zip", "storage-health-csv.zip"
    if export_format == "excel":
        return (
            _excel_bytes(sections, report, time_zone),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "storage-health.xlsx",
        )
    if export_format == "pdf":
        return _pdf_bytes(sections, report, time_zone), "application/pdf", "storage-health.pdf"
    raise ValueError("unsupported export format")
