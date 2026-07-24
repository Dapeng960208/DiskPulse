# -*- coding: utf-8 -*-
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock


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
        _envelope(
            source="vendor_event",
            severity="critical",
            value={"severity": "critical", "association_type": "fault_log"},
        ),
        category="device_fault",
        now=UTC_NOW,
    ) is True
    assert analytics.should_admit_incident(
        _envelope(
            source="vendor_event",
            severity="critical",
            value={"severity": "critical", "association_type": "system_activity"},
        ),
        category="device_fault",
        now=UTC_NOW,
    ) is False
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


def test_incident_ai_review_queue_drain_tolerates_session_adapter_without_info():
    from celery_tasks.tasks import forecast_incidents as tasks

    assert tasks._drain_incident_ai_review_ids(SimpleNamespace()) == set()


def test_vendor_info_and_warning_events_stay_in_system_events_without_creating_incidents(monkeypatch):
    from celery_tasks.tasks import forecast_incidents as tasks
    from crud import forecastIncidentCrud, vendorEventDefinitionCrud
    from services import vendorEventDefinitionService

    cluster = SimpleNamespace(id=7, storage_type="netapp", name="cluster-7")
    events = [
        SimpleNamespace(id=1, source="netapp", external_event_id="critical", severity="critical", related_info={"event_code": "disk.offline"}, updated_at=UTC_NOW),
        SimpleNamespace(id=2, source="netapp", external_event_id="warning", severity="warning", related_info={"event_code": "disk.offline"}, updated_at=UTC_NOW),
        SimpleNamespace(id=3, source="netapp", external_event_id="info", severity="info", related_info={"event_code": "disk.offline"}, updated_at=UTC_NOW),
        SimpleNamespace(id=4, source="netapp", external_event_id="activity", severity="critical", related_info={"event_code": "system.activity"}, updated_at=UTC_NOW),
        SimpleNamespace(id=5, source="netapp", external_event_id="pending", severity="critical", related_info={"event_code": "pending.fault"}, updated_at=UTC_NOW),
        SimpleNamespace(id=6, source="netapp", external_event_id="disabled", severity="critical", related_info={"event_code": "disabled.activity"}, updated_at=UTC_NOW),
    ]
    session = _VendorEventSession(cluster, events)
    recorded = []
    monkeypatch.setattr(tasks, "SessionLocal", lambda: nullcontext(session))
    monkeypatch.setattr(tasks, "_notifications_after_commit", lambda _notifications: None)
    monkeypatch.setattr(tasks, "_record_correlation", lambda _db, **kwargs: recorded.append(kwargs["envelope"]))
    monkeypatch.setattr(
        forecastIncidentCrud,
        "list_existing_incident_evidence_source_refs",
        lambda *_args, **_kwargs: set(),
        raising=False,
    )
    definition_loader = Mock(
        return_value={
            ("netapp", "disk.offline"): SimpleNamespace(
                is_active=True,
                review_status="reviewed",
                association_type="fault_log",
            ),
            ("netapp", "system.activity"): SimpleNamespace(
                is_active=True,
                review_status="reviewed",
                association_type="system_activity",
            ),
            ("netapp", "pending.fault"): SimpleNamespace(
                is_active=True,
                review_status="pending",
                association_type="fault_log",
            ),
            ("netapp", "disabled.activity"): SimpleNamespace(
                is_active=False,
                review_status="reviewed",
                association_type="system_activity",
            ),
        }
    )
    monkeypatch.setattr(
        vendorEventDefinitionCrud,
        "get_definition_map",
        definition_loader,
        raising=False,
    )
    resolver = Mock(
        side_effect=lambda _db, _storage_type, event_code: {
            "association_type": (
                "system_activity" if event_code == "system.activity" else "fault_log"
            )
        }
    )
    monkeypatch.setattr(
        vendorEventDefinitionService,
        "resolve_definition",
        resolver,
    )

    handled = tasks.process_vendor_event_evidence(storage_cluster_id=7)

    assert handled == 3
    assert [item.source_ref for item in recorded] == [
        "storage_alert:1",
        "storage_alert:5",
        "storage_alert:6",
    ]
    assert [item.value["association_type"] for item in recorded] == [
        "fault_log",
        "unknown",
        "unknown",
    ]
    assert definition_loader.call_count == 1
    assert resolver.call_count == 0


def test_vendor_event_upgrade_replay_skips_existing_legacy_evidence_reference(
    monkeypatch,
):
    from celery_tasks.tasks import forecast_incidents as tasks
    from crud import forecastIncidentCrud, vendorEventDefinitionCrud

    cluster = SimpleNamespace(id=7, storage_type="netapp", name="cluster-7")
    event = SimpleNamespace(
        id=9,
        source="netapp",
        external_event_id="legacy-external-9",
        severity="critical",
        related_info={"event_code": "disk.offline"},
        updated_at=UTC_NOW,
    )
    session = _VendorEventSession(cluster, [event])
    recorded = []
    monkeypatch.setattr(tasks, "SessionLocal", lambda: nullcontext(session))
    monkeypatch.setattr(tasks, "_notifications_after_commit", lambda _notifications: None)
    monkeypatch.setattr(
        tasks,
        "_record_correlation",
        lambda _db, **kwargs: recorded.append(kwargs["envelope"]),
    )
    monkeypatch.setattr(
        vendorEventDefinitionCrud,
        "get_definition_map",
        lambda *_args, **_kwargs: {
            ("netapp", "disk.offline"): SimpleNamespace(
                is_active=True,
                review_status="reviewed",
                association_type="fault_log",
            )
        },
    )
    existing_loader = Mock(return_value={"netapp:legacy-external-9"})
    monkeypatch.setattr(
        forecastIncidentCrud,
        "list_existing_incident_evidence_source_refs",
        existing_loader,
        raising=False,
    )

    handled = tasks.process_vendor_event_evidence(storage_cluster_id=7)

    assert handled == 0
    assert recorded == []
    existing_loader.assert_called_once()
    requested_refs = existing_loader.call_args.kwargs["source_refs"]
    assert set(requested_refs) == {
        "storage_alert:9",
        "netapp:legacy-external-9",
    }


def test_vendor_event_asset_uses_stable_node_identity_without_a_false_mapping_gap():
    from celery_tasks.tasks import forecast_incidents as tasks

    cluster = SimpleNamespace(id=7, storage_type="netapp", name="cluster-7")
    event = SimpleNamespace(
        source="netapp",
        related_type="node",
        related_info={
            "object_id": "node-uuid-7",
            "raw": {"node": {"uuid": "node-uuid-7", "name": "node-a"}},
        },
    )

    asset, quality = tasks._vendor_event_asset(cluster, event)

    assert quality == "good"
    assert asset.asset_type == "storage_node"
    assert asset.asset_id == "node-uuid-7"
    assert asset.storage_cluster_id == 7
    assert asset.display_name == "node-a"


def test_vendor_event_wall_time_is_converted_from_asia_shanghai_to_utc(monkeypatch):
    from celery_tasks.tasks import forecast_incidents as tasks
    from crud import forecastIncidentCrud

    cluster = SimpleNamespace(id=7, storage_type="netapp", name="cluster-7")
    event = SimpleNamespace(
        id=1,
        source="netapp",
        external_event_id="node-a:334142",
        severity="critical",
        updated_at=datetime(2026, 7, 21, 1, 3, 30),
    )
    session = _VendorEventSession(cluster, [event])
    recorded = []
    monkeypatch.setattr(tasks, "SessionLocal", lambda: nullcontext(session))
    monkeypatch.setattr(tasks, "_vendor_event_asset", lambda *_args: (_asset(), "good"))
    monkeypatch.setattr(tasks, "_notifications_after_commit", lambda _notifications: None)
    monkeypatch.setattr(tasks, "_record_correlation", lambda _db, **kwargs: recorded.append(kwargs["envelope"]))
    monkeypatch.setattr(
        forecastIncidentCrud,
        "list_existing_incident_evidence_source_refs",
        lambda *_args, **_kwargs: set(),
        raising=False,
    )

    assert tasks.process_vendor_event_evidence(storage_cluster_id=7) == 1
    assert recorded[0].observed_at == datetime(2026, 7, 20, 17, 3, 30, tzinfo=timezone.utc)
