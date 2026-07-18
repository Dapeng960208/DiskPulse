# -*- coding: utf-8 -*-
"""Pure contracts for the storage-space performance monitoring read path."""

METRICS = {
    "latency_read": ("读延迟", "ms"),
    "latency_write": ("写延迟", "ms"),
    "latency_total": ("总延迟", "ms"),
    "iops_total": ("IOPS", "IOPS"),
    "throughput_total": ("吞吐量", "B/s"),
}
DEFAULT_METRICS = ("latency_total", "iops_total", "throughput_total")


def validate_metrics(metrics: list[str] | None) -> tuple[str, ...]:
    selected = tuple(metrics or DEFAULT_METRICS)
    if len(selected) > len(METRICS):
        raise ValueError("at most 5 performance metrics are supported")
    if not selected or any(metric not in METRICS for metric in selected):
        raise ValueError("unsupported performance metric")
    return tuple(dict.fromkeys(selected))


def resolve_performance_identity(*, performance_object_id, volume_name, candidate_ids, candidate_names):
    if performance_object_id and performance_object_id in candidate_ids:
        return performance_object_id, "stable_id"
    return None, "unmatched"
