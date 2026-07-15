# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship

from database import Base


class StorageConf(Base):
    __tablename__ = "storage_conf"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="storage conf")
    iam_url = Column(String)
    iam_account = Column(String)
    iam_password = Column(String)
    bpm_api_url = Column(String)
    bpm_process_id = Column(Integer, default=31)
    mail_host = Column(String)
    mail_port = Column(Integer, default=587)
    mail_to = Column(String)
    mail_user = Column(String)
    mail_password = Column(String)
    storage_host = Column(String)
    storage_port = Column(Integer, default=22)
    storage_user = Column(String)
    storage_password = Column(String)
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
    is_alert = Column(Boolean, default=False)
    in_charge_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    pt_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    limit = Column(Float, default=0)
    soft_limit = Column(Float, nullable=True)
    used = Column(Float, default=0)
    use_ratio = Column(Float, default=0)
    soft_use_ratio = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.now)

    groups = relationship("Group", back_populates="project", lazy=True)
    in_charge_user = relationship("User", foreign_keys=[in_charge_user_id], lazy=True)
    pt_user = relationship("User", foreign_keys=[pt_user_id], lazy=True)


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
    updated_at = Column(DateTime, default=datetime.now)

    storage_cluster = relationship("StorageCluster", lazy=True)


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
