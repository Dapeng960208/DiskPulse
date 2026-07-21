# -*- coding: utf-8 -*-
"""Conservative repair of legacy incidents created from non-critical vendor events."""

from datetime import datetime

from sqlalchemy import select

from crud import forecastIncidentCrud, storageHealthAnalyticsCrud
from models import Incident, IncidentTimeline


_CRITICAL_SEVERITIES = {"alert", "critical", "emergency", "high"}


def _legacy_noncritical_vendor_incident(
    incident: Incident,
    evidence_by_incident,
    alerts_by_reference,
) -> bool:
    evidence = evidence_by_incident.get(incident.id, [])
    if not evidence:
        return False
    alerts = [
        alerts_by_reference.get((incident.storage_cluster_id, item.source_ref))
        for item in evidence
    ]
    # Unknown or mixed evidence is not safe to repair automatically.
    if any(alert is None for alert in alerts):
        return False
    return all(
        str(alert.severity or "info").strip().lower() not in _CRITICAL_SEVERITIES
        for alert in alerts
    )


def reconcile_legacy_vendor_incidents(
    db,
    dry_run: bool,
    now: datetime,
) -> dict[str, int]:
    incidents = db.execute(
        select(Incident)
        .where(
            Incident.category == "device_fault",
            Incident.status != "resolved",
        )
        .order_by(Incident.id)
    ).scalars().all()
    evidence_rows = forecastIncidentCrud.list_incident_evidence_for_incidents(
        db,
        (incident.id for incident in incidents),
    )
    evidence_by_incident = {}
    for evidence in evidence_rows:
        evidence_by_incident.setdefault(evidence.incident_id, []).append(evidence)
    cluster_by_incident = {
        incident.id: incident.storage_cluster_id for incident in incidents
    }
    alerts_by_reference = (
        storageHealthAnalyticsCrud.get_vendor_alerts_for_cluster_evidence_refs(
            db,
            (
                (cluster_by_incident.get(evidence.incident_id), evidence.source_ref)
                for evidence in evidence_rows
            ),
        )
    )
    candidates = [
        incident
        for incident in incidents
        if _legacy_noncritical_vendor_incident(
            incident,
            evidence_by_incident,
            alerts_by_reference,
        )
    ]
    result = {
        "scanned": len(incidents),
        "would_close": len(candidates),
        "closed": 0,
    }
    if dry_run:
        return result

    for incident in candidates:
        previous_status = incident.status
        incident.status = "resolved"
        incident.resolved_at = now
        incident.updated_at = now
        db.add(
            IncidentTimeline(
                incident_id=incident.id,
                event_type="reconciled",
                from_status=previous_status,
                to_status="resolved",
                comment=(
                    "系统复核历史厂商事件证据后确认："
                    "所有关联记录均非严重故障，已关闭该历史误分类事件。"
                ),
                occurred_at=now,
            )
        )
    db.flush()
    result["closed"] = len(candidates)
    return result
