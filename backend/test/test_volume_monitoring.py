# -*- coding: utf-8 -*-
import pytest

def test_volume_monitoring_metrics_are_allowlisted_and_limited():
    from services.volumeMonitoringService import validate_metrics

    assert validate_metrics(None) == ("latency_total", "iops_total", "throughput_total")
    assert validate_metrics(["iops_total", "latency_read"]) == ("iops_total", "latency_read")
    with pytest.raises(ValueError, match="unsupported performance metric"):
        validate_metrics(["drop table"])
    with pytest.raises(ValueError, match="at most 5"):
        validate_metrics(["latency_read"] * 6)


def test_performance_identity_requires_stable_id_and_leaves_unmatched_volume_empty():
    from services.volumeMonitoringService import resolve_performance_identity

    assert resolve_performance_identity(
        performance_object_id="netapp-uuid", volume_name="vol-a", candidate_ids={"netapp-uuid"}, candidate_names=set()
    ) == ("netapp-uuid", "stable_id")
    assert resolve_performance_identity(
        performance_object_id="netapp-uuid", volume_name="vol-a", candidate_ids=set(), candidate_names={"vol-a"}
    ) == (None, "unmatched")
    assert resolve_performance_identity(
        performance_object_id=None, volume_name="vol-a", candidate_ids=set(), candidate_names=set()
    ) == (None, "unmatched")


def test_volume_monitoring_declares_tb_for_its_capacity_curve():
    from schemas.volumeSchema import VolumeMonitoring

    assert VolumeMonitoring.model_fields["capacity_unit"].default == "TB"
