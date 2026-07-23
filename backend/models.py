# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    desc,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import backref, relationship

from database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Persist telemetry ledger timestamps as UTC-aware datetimes."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Telemetry timestamps must include a timezone")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class StorageConf(Base):
    __tablename__ = "storage_conf"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="storage conf")
    mail_host = Column(String)
    mail_port = Column(Integer, default=587)
    mail_to = Column(String)
    mail_user = Column(String)
    mail_password = Column(String)
    domain_name = Column(String)
    person_expand = Column(String)
    group_expand = Column(String)
    company = Column(String)
    file_manage_host = Column(String)
    file_manage_port = Column(Integer, default=22)
    file_manage_user = Column(String)
    file_manage_password = Column(String)
    back_up_enabled = Column(Boolean, default=False)
    back_up_dir = Column(String)
    back_up_duration = Column(Integer, default=60)
    back_up_quit_days = Column(Integer, default=30)
    storage_alert_rule = Column(JSON, nullable=False, default=lambda: {
        "quota_basis": "hard",
        "important": {"threshold": 80, "repeat_hours": 24},
        "serious": {"threshold": 90, "repeat_hours": 6},
        "emergency": {"threshold": 95, "repeat_hours": 1},
    })


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    iam_id = Column(Integer, nullable=True)
    uid = Column(Integer, nullable=True)
    avatar_url = Column(String, nullable=True)
    username = Column(String, nullable=True)
    rd_username = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, nullable=True)
    department = Column(String, nullable=True)
    is_alert = Column(Boolean, default=True)
    user_type = Column(Integer, default=2)
    storage_used = Column(Float, default=0)
    quit_days = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.now)

    storage_usages = relationship("StorageUsage", back_populates="user", passive_deletes=True)


class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    ip = Column(String, nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    descriptions = Column(Text, nullable=True)
    is_common = Column(Boolean, default=False)
    status = Column(Integer, default=1)
    project_process_code = Column(String, nullable=True)
    recipients = Column(String, nullable=True)
    is_alert = Column(Boolean, default=True)
    storage_alert_rule = Column(JSON, nullable=True)
    in_charge_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    limit = Column(Float, default=0)
    soft_limit = Column(Float, nullable=True)
    used = Column(Float, default=0)
    use_ratio = Column(Float, default=0)
    soft_use_ratio = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.now)

    groups = relationship("Group", back_populates="project", lazy=True)
    in_charge_user = relationship("User", foreign_keys=[in_charge_user_id], lazy=True)


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_membership_user"),
        CheckConstraint(
            "role IN ('reader', 'editor', 'project_admin')",
            name="ck_project_membership_role",
        ),
        Index("ix_project_membership_user_project", "user_id", "project_id"),
        Index("ix_project_membership_project_role", "project_id", "role"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False, default="reader")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("phase IN ('attempt', 'result')", name="ck_audit_event_phase"),
        CheckConstraint("outcome IN ('success', 'denied', 'failure')", name="ck_audit_event_outcome"),
        Index("ix_audit_events_project_occurred_id", "project_id", "occurred_at", "id"),
        Index("ix_audit_events_actor_occurred_id", "actor_user_id", "occurred_at", "id"),
        Index("ix_audit_events_operation_occurred", "operation_id", "occurred_at"),
    )

    id = Column(String(36), primary_key=True)
    operation_id = Column(String(36), nullable=False)
    phase = Column(String(16), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=datetime.now)
    actor_type = Column(String(32), nullable=False)
    # Audit rows retain historical logical IDs even after the referenced subject is removed.
    # Foreign-key SET NULL would mutate this append-only table and be rejected by its trigger.
    actor_user_id = Column(Integer, nullable=True)
    action = Column(String(128), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(Integer, nullable=True)
    project_id = Column(Integer, nullable=True)
    outcome = Column(String(16), nullable=False)
    reason_code = Column(String(128), nullable=True)
    before_summary = Column(JSON, nullable=True)
    after_summary = Column(JSON, nullable=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    request_id = Column(String(36), nullable=False)
    trace_id = Column(String(36), nullable=False)


class StorageCluster(Base):
    __tablename__ = "storage_clusters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    storage_type = Column(String, nullable=False)
    storage_host = Column(String)
    storage_port = Column(Integer, default=22)
    protocol = Column(String(8), default="https", nullable=False)
    tls_verify = Column(Boolean, default=True, nullable=False)
    storage_user = Column(String)
    storage_password = Column(String)
    isilon_session_cache_mode = Column(String(16), nullable=False, default="none")
    isilon_session_cache_path = Column(String(1024), nullable=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    limit = Column(Float)
    used = Column(Float)
    use_ratio = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

    aggregates = relationship("Aggregate", back_populates="storage_cluster", lazy=True)
    volumes = relationship("Volume", back_populates="storage_cluster", lazy=True)
    qtrees = relationship("Qtree", back_populates="storage_cluster", lazy=True)
    storage_usages = relationship("StorageUsage", back_populates="storage_cluster", lazy=True)
    groups = relationship("Group", back_populates="storage_cluster", lazy=True)


class TelemetryCollectionRun(Base):
    __tablename__ = "telemetry_collection_runs"
    __table_args__ = (
        UniqueConstraint("task_id", "attempt", "component", "scope_key", name="uq_telemetry_run_task_attempt_scope"),
        CheckConstraint("attempt >= 1", name="ck_telemetry_run_attempt"),
        CheckConstraint("scope_type IN ('cluster', 'scheduler')", name="ck_telemetry_run_scope_type"),
        CheckConstraint("component IN ('capacity', 'vendor_events', 'performance')", name="ck_telemetry_run_component"),
        CheckConstraint("outcome IS NULL OR outcome IN ('success', 'failed', 'skipped')", name="ck_telemetry_run_outcome"),
        CheckConstraint("data_state IS NULL OR data_state IN ('data', 'empty', 'unsupported')", name="ck_telemetry_run_data_state"),
        CheckConstraint(
            "error_code IS NULL OR error_code IN ('vendor_auth', 'vendor_timeout', 'postgres', 'questdb', 'unknown')",
            name="ck_telemetry_run_error_code",
        ),
        CheckConstraint(
            "(scope_type = 'cluster' AND scope_key <> '') OR "
            "(scope_type = 'scheduler' AND scope_key = 'scheduler' AND storage_cluster_id IS NULL)",
            name="ck_telemetry_run_scope",
        ),
        CheckConstraint(
            "(outcome IS NULL AND finished_at IS NULL AND data_state IS NULL "
            "AND records_written IS NULL AND error_code IS NULL) OR "
            "(outcome IS NOT NULL AND finished_at IS NOT NULL AND ((outcome = 'success' AND data_state IS NOT NULL "
            "AND records_written IS NOT NULL AND error_code IS NULL) OR "
            "(outcome = 'failed' AND data_state IS NULL AND records_written IS NULL AND error_code IS NOT NULL) OR "
            "(outcome = 'skipped' AND data_state IS NULL AND records_written IS NULL AND error_code IS NULL)))",
            name="ck_telemetry_run_terminal_fields",
        ),
        Index(
            "ix_telemetry_run_component_cluster_finished",
            "component",
            "storage_cluster_id",
            desc("finished_at"),
        ),
        Index("ix_telemetry_run_created_at", "created_at"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(String(128), nullable=False)
    attempt = Column(Integer, nullable=False)
    scope_type = Column(String(16), nullable=False)
    scope_key = Column(String(64), nullable=False)
    storage_cluster_id = Column(
        Integer,
        ForeignKey("storage_clusters.id", ondelete="SET NULL"),
        nullable=True,
    )
    component = Column(String(32), nullable=False)
    trace_id = Column(String(36), nullable=False)
    started_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    finished_at = Column(UTCDateTime(), nullable=True)
    outcome = Column(String(16), nullable=True)
    data_state = Column(String(16), nullable=True)
    records_written = Column(Integer, nullable=True)
    error_code = Column(String(32), nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)

    storage_cluster = relationship("StorageCluster", lazy=True)


class GroupTag(Base):
    __tablename__ = "group_tags"
    __table_args__ = (UniqueConstraint("name", name="uq_group_tag_name"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)

    groups = relationship("Group", back_populates="group_tag", lazy=True)


class Aggregate(Base):
    __tablename__ = "aggregates"

    id = Column(Integer, primary_key=True, index=True)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id"), nullable=True, index=True)
    name = Column(String, index=True)
    limit = Column(Float, default=0)
    used = Column(Float, default=0)
    use_ratio = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.now)

    storage_cluster = relationship("StorageCluster", back_populates="aggregates", lazy=True)


class Volume(Base):
    __tablename__ = "volumes"

    id = Column(Integer, primary_key=True, index=True)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id"), nullable=True, index=True)
    name = Column(String, index=True)
    vserver = Column(String)
    aggregate = Column(String)
    state = Column(String)
    type = Column(String)
    limit = Column(Float, default=0)
    soft_limit = Column(Float, nullable=True)
    used = Column(Float, default=0)
    use_ratio = Column(Float, default=0)
    soft_use_ratio = Column(Float, nullable=True)
    allocated = Column(Float, default=0)
    performance_object_id = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.now)

    qtrees = relationship("Qtree", back_populates="volume", lazy=True)
    storage_cluster = relationship("StorageCluster", back_populates="volumes", lazy=True)


class Qtree(Base):
    __tablename__ = "qtrees"

    id = Column(Integer, primary_key=True, index=True)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id"), nullable=True, index=True)
    volume_id = Column(Integer, ForeignKey("volumes.id"), nullable=True)
    name = Column(String, index=True)
    limit = Column(Float, default=0)
    soft_limit = Column(Float, nullable=True)
    used = Column(Float, default=0)
    use_ratio = Column(Float, default=0)
    soft_use_ratio = Column(Float, nullable=True)
    style = Column(String)
    oplocks = Column(String)
    status = Column(String)
    updated_at = Column(DateTime, default=datetime.now)

    volume = relationship("Volume", back_populates="qtrees", lazy=True)
    groups = relationship("Group", back_populates="qtree", lazy=True)
    storage_cluster = relationship("StorageCluster", back_populates="qtrees", lazy=True)


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "storage_cluster_id",
            "group_tag_id",
            "name",
            name="uq_group_scope_name",
        ),
        CheckConstraint(
            "volume_id IS NULL OR qtree_id IS NULL",
            name="ck_group_single_storage_target",
        ),
        CheckConstraint(
            "enable_monitoring = FALSE OR volume_id IS NOT NULL OR qtree_id IS NOT NULL",
            name="ck_group_monitored_has_storage_target",
        ),
        Index(
            "ix_group_project_cluster_tag",
            "project_id",
            "storage_cluster_id",
            "group_tag_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", name="fk_group_project"),
        nullable=False,
    )
    storage_cluster_id = Column(
        Integer,
        ForeignKey("storage_clusters.id", name="fk_group_storage_cluster"),
        nullable=False,
    )
    group_tag_id = Column(
        Integer,
        ForeignKey("group_tags.id", name="fk_group_tag"),
        nullable=False,
    )
    monitor_host_id = Column(Integer, nullable=True)
    volume_id = Column(
        Integer,
        ForeignKey("volumes.id", name="fk_group_volume"),
        nullable=True,
    )
    qtree_id = Column(Integer, ForeignKey("qtrees.id"), nullable=True)
    in_charge_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, index=True)
    linux_path = Column(String, index=True)
    back_path = Column(String)
    limit = Column(Float, default=0)
    soft_limit = Column(Float, nullable=True)
    used = Column(Float, default=0)
    use_ratio = Column(Float, default=0)
    soft_use_ratio = Column(Float, nullable=True)
    associated_mail_groups = Column(String)
    associate_multiple_groups = Column(Boolean, default=False)
    enable_monitoring = Column(Boolean, default=True)
    completed = Column(Boolean, default=False)
    back_up_enabled = Column(Boolean, default=True)
    storage_alert_rule = Column(JSON, nullable=True)
    alert_cc_user_ids = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime, default=datetime.now)

    qtree = relationship("Qtree", back_populates="groups", lazy=True)
    project = relationship("Project", back_populates="groups", lazy=True)
    storage_cluster = relationship("StorageCluster", back_populates="groups", lazy=True)
    group_tag = relationship("GroupTag", back_populates="groups", lazy=True)
    volume = relationship("Volume", lazy=True)
    storage_usages = relationship("StorageUsage", back_populates="group", lazy=True)
    in_charge_user = relationship("User", backref=backref("owned_groups", passive_deletes=True))


class StorageUsage(Base):
    __tablename__ = "storage_usages"

    id = Column(Integer, primary_key=True, index=True)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    linux_path = Column(String, index=True)
    limit = Column(Float, default=0)
    soft_limit = Column(Float, nullable=True)
    used = Column(Float, default=0)
    use_ratio = Column(Float, default=0)
    soft_use_ratio = Column(Float, nullable=True)
    file_used = Column(Float, default=0)
    file_limit = Column(Float, default=0)
    size = Column(Integer, default=0)
    blocks = Column(Float, default=0)
    io_block = Column(Float, default=0)
    type = Column(String, default="")
    device = Column(String, default="")
    inode = Column(String, default="")
    links = Column(Integer, default=0)
    access = Column(String, default="")
    gid = Column(String, default="")
    access_time = Column(DateTime)
    modify_time = Column(DateTime)
    change_time = Column(DateTime)
    birth_time = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now)

    group = relationship("Group", back_populates="storage_usages", lazy=True)
    user = relationship("User", back_populates="storage_usages", lazy=True)
    storage_cluster = relationship("StorageCluster", back_populates="storage_usages", lazy=True)


class StorageAlerts(Base):
    __tablename__ = "storage_alerts"
    __table_args__ = (
        UniqueConstraint(
            "storage_cluster_id",
            "source",
            "external_event_id",
            name="uq_storage_alert_vendor_event",
        ),
        Index(
            "ix_storage_alert_cluster_updated",
            "storage_cluster_id",
            "updated_at",
        ),
        Index("ix_storage_alert_severity_updated", "severity", "updated_at"),
        Index("ix_storage_alert_fingerprint_updated", "fingerprint", "updated_at"),
        Index("ix_storage_alert_delivery_due", "delivery_status", "next_attempt_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    storage_cluster_id = Column(
        Integer,
        ForeignKey("storage_clusters.id", ondelete="CASCADE"),
        nullable=True,
    )
    source = Column(String(32), nullable=False, default="diskpulse")
    external_event_id = Column(String(255), nullable=True)
    fingerprint = Column(String(512), nullable=True)
    severity = Column(String(16), nullable=False, default="info")
    alert_level = Column(String)
    alert_type = Column(String)
    description = Column(Text)
    threshold = Column(Integer, default=0)
    avg_use_ratio = Column(Float, default=0)
    related_id = Column(Integer, index=True)
    related_type = Column(String, index=True)
    related_info = Column(JSON)
    event_type = Column(String(16), nullable=False, default="trigger")
    quota_basis = Column(String(8), nullable=False, default="hard")
    delivery_status = Column(String(16), nullable=False, default="legacy")
    recipient_usernames = Column(JSON, nullable=True)
    delivery_attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    notified_at = Column(DateTime, nullable=True)
    delivery_error = Column(String(512), nullable=True)
    updated_at = Column(DateTime, default=datetime.now)

    storage_cluster = relationship("StorageCluster", lazy=True)


class VendorEventDefinition(Base):
    __tablename__ = "vendor_event_definitions"
    __table_args__ = (
        UniqueConstraint(
            "storage_type",
            "event_code",
            name="uq_vendor_event_definition_storage_code",
        ),
        CheckConstraint(
            "storage_type IN ('netapp', 'isilon')",
            name="ck_vendor_event_definition_storage_type",
        ),
        CheckConstraint(
            "association_type IN ("
            "'fault_log', 'performance_anomaly', 'capacity_threshold', "
            "'system_activity', 'telemetry_degradation', 'unknown'"
            ")",
            name="ck_vendor_event_definition_association_type",
        ),
        CheckConstraint(
            "default_severity IS NULL OR default_severity IN ("
            "'critical', 'error', 'warning', 'info'"
            ")",
            name="ck_vendor_event_definition_default_severity",
        ),
        CheckConstraint(
            "review_status IN ('reviewed', 'pending')",
            name="ck_vendor_event_definition_review_status",
        ),
        CheckConstraint(
            "review_status <> 'reviewed' OR ("
            "association_type <> 'unknown' "
            "AND official_reference_url IS NOT NULL "
            "AND trim(official_reference_url) <> '' "
            "AND official_reference_url NOT LIKE '%@%' "
            "AND official_reference_url NOT LIKE '% %' "
            "AND ((storage_type = 'netapp' AND ("
            "lower(official_reference_url) LIKE 'https://netapp.com/%' "
            "OR lower(official_reference_url) LIKE 'https://%.netapp.com/%'"
            ")) OR (storage_type = 'isilon' AND ("
            "lower(official_reference_url) LIKE 'https://dell.com/%' "
            "OR lower(official_reference_url) LIKE 'https://%.dell.com/%' "
            "OR lower(official_reference_url) LIKE 'https://delltechnologies.com/%' "
            "OR lower(official_reference_url) LIKE 'https://%.delltechnologies.com/%'"
            "))) "
            "AND version_scope IS NOT NULL "
            "AND trim(version_scope) <> '' "
            "AND recommended_solution_zh IS NOT NULL "
            "AND trim(recommended_solution_zh) <> ''"
            ")",
            name="ck_vendor_event_definition_reviewed_evidence",
        ),
        Index(
            "ix_vendor_event_definition_filters",
            "storage_type",
            "association_type",
            "review_status",
        ),
        Index("ix_vendor_event_definition_event_code", "event_code"),
    )

    id = Column(Integer, primary_key=True)
    storage_type = Column(String(32), nullable=False)
    event_code = Column(String(255), nullable=False)
    association_type = Column(String(32), nullable=False, default="unknown")
    title_zh = Column(String(255), nullable=False)
    description_zh = Column(Text, nullable=False)
    official_reference_url = Column(String(1000), nullable=True)
    default_severity = Column(String(16), nullable=True)
    version_scope = Column(String(255), nullable=True)
    review_status = Column(String(16), nullable=False, default="pending")
    recommended_solution_zh = Column(Text, nullable=True, comment="推荐解决方案（中文）")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )


class TelemetryQualitySnapshot(Base):
    __tablename__ = "telemetry_quality_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "asset_type", "asset_id", "period", "algorithm_version", "calculated_at",
            name="uq_telemetry_quality_snapshot_version",
        ),
        Index(
            "ix_telemetry_quality_project_period_calculated",
            "project_id", "period", desc("calculated_at"),
        ),
        Index(
            "ix_telemetry_quality_cluster_asset_period",
            "storage_cluster_id", "asset_type", "asset_id", "period",
        ),
    )

    id = Column(Integer, primary_key=True)
    asset_type = Column(String(32), nullable=False)
    asset_id = Column(String(128), nullable=False)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    vendor = Column(String(32), nullable=False)
    display_name = Column(String(255), nullable=False)
    period = Column(String(32), nullable=False)
    latest_point_at = Column(UTCDateTime(), nullable=True)
    coverage_ratio = Column(Float, nullable=False, default=0)
    data_gaps = Column(JSON, nullable=False, default=list)
    quality_status = Column(String(24), nullable=False, default="insufficient")
    algorithm_version = Column(String(64), nullable=False)
    calculated_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class CapacityForecast(Base):
    __tablename__ = "capacity_forecasts"
    __table_args__ = (
        UniqueConstraint(
            "asset_type", "asset_id", "training_end", "algorithm_version",
            name="uq_capacity_forecast_asset_training_version",
        ),
        Index("ix_capacity_forecast_project_created", "project_id", desc("created_at")),
        Index("ix_capacity_forecast_cluster_asset_created", "storage_cluster_id", "asset_type", "asset_id", desc("created_at")),
    )

    id = Column(Integer, primary_key=True)
    asset_type = Column(String(32), nullable=False)
    asset_id = Column(String(128), nullable=False)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    vendor = Column(String(32), nullable=False)
    display_name = Column(String(255), nullable=False)
    training_start = Column(UTCDateTime(), nullable=False)
    training_end = Column(UTCDateTime(), nullable=False)
    hard_limit = Column(Float, nullable=False)
    curve = Column(JSON, nullable=False, default=list)
    exhaustion_dates = Column(JSON, nullable=False, default=dict)
    algorithm_version = Column(String(64), nullable=False)
    input_quality = Column(JSON, nullable=False, default=dict)
    backtest_mape = Column(Float, nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class CapacityPredictionSettings(Base):
    __tablename__ = "capacity_prediction_settings"

    id = Column(Integer, primary_key=True)
    user_visible = Column(Boolean, nullable=False, default=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)


class CapacityPredictionPlan(Base):
    __tablename__ = "capacity_prediction_plans"
    __table_args__ = (
        CheckConstraint("asset_type IN ('group', 'storage_usage')", name="ck_capacity_prediction_plan_asset_type"),
        Index("ix_capacity_prediction_plan_asset_effective", "asset_type", "asset_id", "effective_at"),
        Index("ix_capacity_prediction_plan_project_effective", "project_id", "effective_at"),
    )

    id = Column(Integer, primary_key=True)
    asset_type = Column(String(32), nullable=False)
    asset_id = Column(String(128), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    effective_at = Column(UTCDateTime(), nullable=False)
    capacity_delta = Column(Float, nullable=False)
    reason = Column(String(500), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class CapacityPredictionCandidate(Base):
    __tablename__ = "capacity_prediction_candidates"
    __table_args__ = (UniqueConstraint("version", name="uq_capacity_prediction_candidate_version"),)

    id = Column(Integer, primary_key=True)
    version = Column(String(64), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    ai_model_id = Column(Integer, ForeignKey("ai_configs.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class CapacityPredictionEvaluation(Base):
    __tablename__ = "capacity_prediction_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "window_start",
            "window_end",
            name="uq_capacity_prediction_evaluation_window",
        ),
        Index("ix_capacity_prediction_eval_candidate_created", "candidate_id", desc("created_at")),
    )

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("capacity_prediction_candidates.id", ondelete="CASCADE"), nullable=False)
    baseline_mape = Column(Float, nullable=False)
    candidate_mape = Column(Float, nullable=False)
    risk_coverage_ok = Column(Boolean, nullable=False)
    window_start = Column(UTCDateTime(), nullable=False)
    window_end = Column(UTCDateTime(), nullable=False)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class CapacityPredictionCandidateForecast(Base):
    __tablename__ = "capacity_prediction_candidate_forecasts"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "asset_type",
            "asset_id",
            "forecast_start",
            name="uq_capacity_prediction_candidate_forecast",
        ),
        CheckConstraint(
            "asset_type IN ('group', 'storage_usage')",
            name="ck_capacity_prediction_candidate_forecast_asset_type",
        ),
        CheckConstraint(
            "source IN ('ai_candidate', 'baseline_fallback')",
            name="ck_capacity_prediction_candidate_forecast_source",
        ),
        Index(
            "ix_capacity_prediction_candidate_forecast_asset_start",
            "asset_type",
            "asset_id",
            desc("forecast_start"),
        ),
    )

    id = Column(Integer, primary_key=True)
    candidate_id = Column(
        Integer,
        ForeignKey("capacity_prediction_candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_type = Column(String(32), nullable=False)
    asset_id = Column(String(128), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    forecast_start = Column(UTCDateTime(), nullable=False)
    baseline_curve = Column(JSON, nullable=False)
    curve = Column(JSON, nullable=False)
    source = Column(String(32), nullable=False)
    fallback_reason = Column(String(64), nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class AnomalyObservation(Base):
    __tablename__ = "anomaly_observations"
    __table_args__ = (
        UniqueConstraint("source", "source_ref", "metric", "algorithm_version", name="uq_anomaly_source_metric_version"),
        Index("ix_anomaly_project_observed", "project_id", desc("observed_at")),
        Index("ix_anomaly_cluster_asset_metric_observed", "storage_cluster_id", "asset_type", "asset_id", "metric", desc("observed_at")),
    )

    id = Column(Integer, primary_key=True)
    asset_type = Column(String(32), nullable=False)
    asset_id = Column(String(128), nullable=False)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    vendor = Column(String(32), nullable=False)
    display_name = Column(String(255), nullable=False)
    metric = Column(String(32), nullable=False)
    observed_at = Column(UTCDateTime(), nullable=False)
    observed_value = Column(Float, nullable=False)
    seasonal_baseline = Column(Float, nullable=False)
    mad = Column(Float, nullable=False)
    robust_z_score = Column(Float, nullable=False)
    severity = Column(String(16), nullable=False)
    evidence_window_start = Column(UTCDateTime(), nullable=False)
    evidence_window_end = Column(UTCDateTime(), nullable=False)
    source = Column(String(64), nullable=False)
    source_ref = Column(String(255), nullable=False)
    input_quality = Column(JSON, nullable=False, default=dict)
    algorithm_version = Column(String(64), nullable=False)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint("correlation_key", "correlation_bucket_at", name="uq_incident_correlation_bucket"),
        CheckConstraint("status IN ('open', 'acknowledged', 'investigating', 'mitigated', 'resolved')", name="ck_incident_status"),
        CheckConstraint("category IN ('capacity_pressure', 'device_fault', 'performance_contention', 'telemetry_blindspot')", name="ck_incident_category"),
        Index("ix_incident_latest_evidence", desc("last_evidence_at"), desc("opened_at"), desc("id")),
        Index("ix_incident_project_status_evidence", "project_id", "status", desc("last_evidence_at"), desc("opened_at"), desc("id")),
        Index("ix_incident_cluster_evidence", "storage_cluster_id", desc("last_evidence_at"), desc("opened_at"), desc("id")),
        Index("ix_incident_correlation_resolved", "correlation_key", "resolved_at"),
    )

    id = Column(Integer, primary_key=True)
    correlation_key = Column(String(512), nullable=False)
    correlation_bucket_at = Column(UTCDateTime(), nullable=False)
    asset_type = Column(String(32), nullable=False)
    asset_id = Column(String(128), nullable=False)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    vendor = Column(String(32), nullable=False)
    display_name = Column(String(255), nullable=False)
    category = Column(String(32), nullable=False)
    severity = Column(String(16), nullable=False, default="warning")
    status = Column(String(16), nullable=False, default="open")
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    opened_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    last_evidence_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    resolved_at = Column(UTCDateTime(), nullable=True)
    silenced_until = Column(UTCDateTime(), nullable=True)
    silence_reason = Column(String(500), nullable=True)
    ai_urgency = Column(String(16), nullable=True)
    ai_urgency_reason = Column(String(1000), nullable=True)
    ai_assessment = Column(JSON, nullable=True)
    ai_analyzed_at = Column(UTCDateTime(), nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    updated_at = Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"
    __table_args__ = (
        UniqueConstraint("source", "source_ref", name="uq_incident_evidence_source_ref"),
        Index("ix_incident_evidence_incident_observed", "incident_id", desc("observed_at")),
    )

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(64), nullable=False)
    source_ref = Column(String(255), nullable=False)
    evidence_type = Column(String(64), nullable=False)
    observed_at = Column(UTCDateTime(), nullable=False)
    data_gaps = Column(JSON, nullable=False, default=list)
    evidence_hash = Column(String(64), nullable=False)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"
    __table_args__ = (Index("ix_incident_timeline_incident_occurred", "incident_id", "occurred_at", "id"),)

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(32), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    from_status = Column(String(16), nullable=True)
    to_status = Column(String(16), nullable=True)
    comment = Column(Text, nullable=True)
    occurred_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class IncidentAiSettings(Base):
    __tablename__ = "incident_ai_settings"

    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    iops_absolute_floor = Column(Float, nullable=False, default=10.0)
    iops_baseline_ratio = Column(Float, nullable=False, default=0.05)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)
    model_bindings = relationship(
        "IncidentAiModelBinding",
        order_by="IncidentAiModelBinding.priority",
        cascade="all, delete-orphan",
        back_populates="settings",
    )


class IncidentAiModelBinding(Base):
    __tablename__ = "incident_ai_model_bindings"
    __table_args__ = (
        UniqueConstraint("settings_id", "ai_model_id", name="uq_incident_ai_model_binding"),
        UniqueConstraint("settings_id", "priority", name="uq_incident_ai_model_priority"),
    )

    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey("incident_ai_settings.id", ondelete="CASCADE"), nullable=False)
    ai_model_id = Column(Integer, ForeignKey("ai_configs.id", ondelete="RESTRICT"), nullable=False)
    priority = Column(Integer, nullable=False)
    settings = relationship("IncidentAiSettings", back_populates="model_bindings")
    ai_model = relationship("AIConfig")


class IncidentAiRun(Base):
    __tablename__ = "incident_ai_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_incident_ai_run_idempotency"),
        Index("ix_incident_ai_run_incident_started", "incident_id", desc("started_at")),
    )

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    trigger = Column(String(32), nullable=False)
    idempotency_key = Column(String(255), nullable=False)
    status = Column(String(16), nullable=False, default="running")
    model_id = Column(Integer, ForeignKey("ai_configs.id", ondelete="SET NULL"), nullable=True)
    model_snapshot = Column(JSON, nullable=True)
    attempt_summary = Column(JSON, nullable=False, default=list)
    input_snapshot = Column(JSON, nullable=False, default=dict)
    assessment = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    started_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    completed_at = Column(UTCDateTime(), nullable=True)


class MaintenanceWindow(Base):
    __tablename__ = "maintenance_windows"
    __table_args__ = (Index("ix_maintenance_project_window", "project_id", "starts_at", "ends_at"),)

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    storage_cluster_id = Column(Integer, ForeignKey("storage_clusters.id", ondelete="SET NULL"), nullable=True)
    asset_type = Column(String(32), nullable=True)
    asset_id = Column(String(128), nullable=True)
    starts_at = Column(UTCDateTime(), nullable=False)
    ends_at = Column(UTCDateTime(), nullable=False)
    reason = Column(String(500), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        UniqueConstraint("incident_id", "algorithm_version", "evidence_digest", name="uq_diagnosis_incident_version_digest"),
        Index("ix_diagnosis_incident_created", "incident_id", desc("created_at")),
    )

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    algorithm_version = Column(String(64), nullable=False)
    candidates = Column(JSON, nullable=False, default=list)
    confidence = Column(String(16), nullable=False)
    evidence_ids = Column(JSON, nullable=False, default=list)
    data_gaps = Column(JSON, nullable=False, default=list)
    evidence_digest = Column(String(64), nullable=False)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class StorageAlertState(Base):
    __tablename__ = "storage_alert_states"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", name="uq_storage_alert_state_target"),
        Index("ix_storage_alert_state_target", "target_type", "target_id"),
    )

    id = Column(Integer, primary_key=True)
    target_type = Column(String(32), nullable=False)
    target_id = Column(Integer, nullable=False)
    rule_signature = Column(String(64), nullable=False)
    consecutive_breach_count = Column(Integer, nullable=False, default=0)
    current_level = Column(String(16), nullable=True)
    last_use_ratio = Column(Float, nullable=True)
    last_observed_at = Column(DateTime, nullable=True)
    last_notified_at = Column(DateTime, nullable=True)


class StorageBackUpRecord(Base):
    __tablename__ = "storage_back_up_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_path = Column(String)
    destination_path = Column(String)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, default=datetime.now)
    status = Column(Integer, default=1)
    process_uid = Column(String, nullable=True)

    user = relationship("User", foreign_keys=[user_id], lazy=True)


class LargeFiles(Base):
    __tablename__ = "large_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    linux_path = Column(String, index=True)
    size = Column(Float, default=0)
    file_type = Column(String, default="other")
    updated_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    group = relationship("Group")


class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    provider = Column(String(50), nullable=False, default="openai")
    base_url = Column(String(500), nullable=False, default="")
    api_key_encrypted = Column(Text, nullable=False, default="")
    model = Column(String(200), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    enable_chat = Column(Boolean, nullable=False, default=True)
    temperature = Column(Numeric(3, 2), nullable=False, default=0.3)
    max_tokens = Column(Integer, nullable=False, default=2048)
    system_prompt = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("ai_configs.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="新对话")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    messages = relationship(
        "AIMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AIMessage.id",
        passive_deletes=True,
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        Integer,
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    conversation = relationship("AIConversation", back_populates="messages")


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"
    __table_args__ = (Index("ix_ai_audit_started_id", "started_at", "id"),)

    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("ai_configs.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("ai_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    source_ref = Column(String(200), nullable=True)
    request_payload = Column(Text, nullable=False, default="")
    response_payload = Column(Text, nullable=False, default="")
    tool_call_count = Column(Integer, nullable=False, default=0)
    tool_failed_count = Column(Integer, nullable=False, default=0)
    detail_payload = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    trace_id = Column(String(64), nullable=True, index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    model = relationship("AIConfig", foreign_keys=[model_id])
    conversation = relationship("AIConversation", foreign_keys=[conversation_id])
    user = relationship("User", foreign_keys=[user_id])
