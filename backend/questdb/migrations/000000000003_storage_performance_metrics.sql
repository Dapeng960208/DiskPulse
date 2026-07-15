CREATE TABLE IF NOT EXISTS storage_performance_metrics (
    storage_cluster_id SYMBOL,
    vendor SYMBOL,
    object_type SYMBOL,
    object_id SYMBOL,
    object_name SYMBOL,
    latency_read DOUBLE,
    latency_write DOUBLE,
    latency_total DOUBLE,
    iops_total DOUBLE,
    throughput_total DOUBLE,
    collected_at TIMESTAMP
) TIMESTAMP(collected_at) PARTITION BY DAY TTL 180 DAYS WAL;
