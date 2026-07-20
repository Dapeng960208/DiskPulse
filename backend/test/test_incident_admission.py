# -*- coding: utf-8 -*-
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace


UTC_NOW = datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc)


def _asset():
    from services.forecastIncidentService import AssetRef

    return AssetRef(
        asset_type="storage_cluster",
        asset_id="7",
        storage_cluster_id=7,
        project_id=None,
        vendor="netapp",
        display_name="cluster-7",
    )


def _envelope(*, source: str, severity: str, value: dict | None = None):
    from services.forecastIncidentService import TelemetryEnvelope

    return TelemetryEnvelope(
        asset_ref=_asset(),
        source=source,
        source_ref=f"{source}:{severity}",
        observed_at=UTC_NOW,
        collected_at=UTC_NOW,
        metric_or_event="test",
        value=value or {"severity": severity},
        quality="good",
    )


def test_incident_admission_keeps_only_urgent_cluster_evidence():
    from services import forecastIncidentService as analytics

    assert analytics.should_admit_incident(
        _envelope(source="vendor_event", severity="critical"),
        category="device_fault",
        now=UTC_NOW,
    ) is True
    assert analytics.should_admit_incident(
        _envelope(source="vendor_event", severity="warning"),
        category="device_fault",
        now=UTC_NOW,
    ) is False
    assert analytics.should_admit_incident(
        _envelope(source="diskpulse_alert", severity="warning"),
        category="capacity_pressure",
        now=UTC_NOW,
    ) is False
    assert analytics.should_admit_incident(
        _envelope(source="diskpulse_alert", severity="critical"),
        category="capacity_pressure",
        now=UTC_NOW,
    ) is True
    assert analytics.should_admit_incident(
        _envelope(source="anomaly_observation", severity="warning"),
        category="performance_contention",
        now=UTC_NOW,
    ) is False
    assert analytics.should_admit_incident(
        _envelope(source="telemetry_quality", severity="critical"),
        category="telemetry_blindspot",
        now=UTC_NOW,
    ) is False
    assert analytics.should_admit_incident(
        _envelope(
            source="capacity_forecast",
            severity="warning",
            value={"severity": "warning", "exhaustion_p90": (UTC_NOW + timedelta(days=7)).isoformat()},
        ),
        category="capacity_pressure",
        now=UTC_NOW,
    ) is True


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _VendorEventSession:
    def __init__(self, cluster, rows):
        self.cluster = cluster
        self.rows = rows

    def get(self, _model, _identity):
        return self.cluster

    def execute(self, _statement):
        return _Result(self.rows)

    def commit(self):
        return None

    def rollback(self):
        return None


def test_vendor_info_and_warning_events_stay_in_system_events_without_creating_incidents(monkeypatch):
    from celery_tasks.tasks import forecast_incidents as tasks

    cluster = SimpleNamespace(id=7, storage_type="netapp", name="cluster-7")
    events = [
        SimpleNamespace(id=1, source="netapp", external_event_id="critical", severity="critical", updated_at=UTC_NOW),
        SimpleNamespace(id=2, source="netapp", external_event_id="warning", severity="warning", updated_at=UTC_NOW),
        SimpleNamespace(id=3, source="netapp", external_event_id="info", severity="info", updated_at=UTC_NOW),
    ]
    session = _VendorEventSession(cluster, events)
    recorded = []
    monkeypatch.setattr(tasks, "SessionLocal", lambda: nullcontext(session))
    monkeypatch.setattr(tasks, "_notifications_after_commit", lambda _notifications: None)
    monkeypatch.setattr(tasks, "_record_correlation", lambda _db, **kwargs: recorded.append(kwargs["envelope"]))

    handled = tasks.process_vendor_event_evidence(storage_cluster_id=7)

    assert handled == 1
    assert [item.source_ref for item in recorded] == ["netapp:critical"]
