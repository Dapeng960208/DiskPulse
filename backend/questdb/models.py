# -*- coding: utf-8 -*-
from questdb_connect import Double, PartitionBy, QDBTableEngine, Symbol, Timestamp
from sqlalchemy import Column

from questdb.database import QuestDBBase


class StorageClusterUsage(QuestDBBase):
    __tablename__ = "storage_cluster_storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="storage_cluster_storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    storage_cluster_id = Column(Symbol, primary_key=True)
    used = Column(Double)
    use_ratio = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class AggregateStorageUsage(QuestDBBase):
    __tablename__ = "aggregate_storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="aggregate_storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    storage_cluster_id = Column(Symbol)
    aggregate_id = Column(Symbol, primary_key=True)
    used = Column(Double)
    used_ratio = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class VolumeStorageUsage(QuestDBBase):
    __tablename__ = "volume_storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="volume_storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    volume_id = Column(Symbol, primary_key=True)
    used = Column(Double)
    used_ratio = Column(Double)
    soft_limit = Column(Double)
    soft_use_ratio = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class QtreeStorageUsage(QuestDBBase):
    __tablename__ = "qtree_storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="qtree_storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    qtree_id = Column(Symbol, primary_key=True)
    used = Column(Double)
    used_ratio = Column(Double)
    soft_limit = Column(Double)
    soft_use_ratio = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class ProjectStorageUsage(QuestDBBase):
    __tablename__ = "project_storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="project_storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    project_id = Column(Symbol, primary_key=True)
    used = Column(Double)
    used_ratio = Column(Double)
    soft_limit = Column(Double)
    soft_use_ratio = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class GroupStorageUsage(QuestDBBase):
    __tablename__ = "group_storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="group_storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    group_id = Column(Symbol, primary_key=True)
    used = Column(Double)
    used_ratio = Column(Double)
    soft_limit = Column(Double)
    soft_use_ratio = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class StorageUsage(QuestDBBase):
    __tablename__ = "storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    storage_usage_id = Column(Symbol, primary_key=True)
    user_id = Column(Symbol)
    used = Column(Double)
    used_ratio = Column(Double)
    file_used = Column(Double)
    soft_limit = Column(Double)
    soft_use_ratio = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class UserStorageUsage(QuestDBBase):
    __tablename__ = "user_storage_usages"
    __table_args__ = (
        QDBTableEngine(
            table_name="user_storage_usages",
            ts_col_name="updated_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    user_id = Column(Symbol, primary_key=True)
    limit = Column(Double)
    soft_limit = Column(Double)
    used = Column(Double)
    use_ratio = Column(Double)
    soft_use_ratio = Column(Double)
    file_used = Column(Double)
    updated_at = Column(Timestamp, primary_key=True)


class StoragePerformanceMetric(QuestDBBase):
    __tablename__ = "storage_performance_metrics"
    __table_args__ = (
        QDBTableEngine(
            table_name="storage_performance_metrics",
            ts_col_name="collected_at",
            partition_by=PartitionBy.DAY,
            is_wal=True,
        ),
    )

    storage_cluster_id = Column(Symbol, primary_key=True)
    vendor = Column(Symbol)
    object_type = Column(Symbol)
    object_id = Column(Symbol, primary_key=True)
    object_name = Column(Symbol)
    latency_read = Column(Double)
    latency_write = Column(Double)
    latency_total = Column(Double)
    iops_total = Column(Double)
    throughput_total = Column(Double)
    collected_at = Column(Timestamp, primary_key=True)
