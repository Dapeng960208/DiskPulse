"""Create the initial DiskPulse schema.

Revision ID: 000000000001
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000001"
down_revision: None = None
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        "hosts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("ip", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hosts_id", "hosts", ["id"], unique=False)

    op.create_table(
        "storage_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_level", sa.String(), nullable=True),
        sa.Column("alert_type", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("avg_use_ratio", sa.Float(), nullable=True),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("related_type", sa.String(), nullable=True),
        sa.Column("related_info", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_storage_alerts_id", "storage_alerts", ["id"], unique=False)
    op.create_index(
        "ix_storage_alerts_related_id",
        "storage_alerts",
        ["related_id"],
        unique=False,
    )
    op.create_index(
        "ix_storage_alerts_related_type",
        "storage_alerts",
        ["related_type"],
        unique=False,
    )

    op.create_table(
        "storage_clusters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("storage_type", sa.String(), nullable=False),
        sa.Column("storage_host", sa.String(), nullable=True),
        sa.Column("storage_port", sa.Integer(), nullable=True),
        sa.Column("storage_user", sa.String(), nullable=True),
        sa.Column("storage_password", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_storage_clusters_id", "storage_clusters", ["id"], unique=False
    )

    op.create_table(
        "storage_conf",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("iam_url", sa.String(), nullable=True),
        sa.Column("iam_account", sa.String(), nullable=True),
        sa.Column("iam_password", sa.String(), nullable=True),
        sa.Column("bpm_api_url", sa.String(), nullable=True),
        sa.Column("bpm_process_id", sa.Integer(), nullable=True),
        sa.Column("mail_host", sa.String(), nullable=True),
        sa.Column("mail_port", sa.Integer(), nullable=True),
        sa.Column("mail_to", sa.String(), nullable=True),
        sa.Column("mail_user", sa.String(), nullable=True),
        sa.Column("mail_password", sa.String(), nullable=True),
        sa.Column("storage_host", sa.String(), nullable=True),
        sa.Column("storage_port", sa.Integer(), nullable=True),
        sa.Column("storage_user", sa.String(), nullable=True),
        sa.Column("storage_password", sa.String(), nullable=True),
        sa.Column("domain_name", sa.String(), nullable=True),
        sa.Column("person_expand", sa.String(), nullable=True),
        sa.Column("group_expand", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("file_manage_host", sa.String(), nullable=True),
        sa.Column("file_manage_port", sa.Integer(), nullable=True),
        sa.Column("file_manage_user", sa.String(), nullable=True),
        sa.Column("file_manage_password", sa.String(), nullable=True),
        sa.Column("back_up_enabled", sa.Boolean(), nullable=True),
        sa.Column("back_up_dir", sa.String(), nullable=True),
        sa.Column("back_up_duration", sa.Integer(), nullable=True),
        sa.Column("back_up_quit_days", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_storage_conf_id", "storage_conf", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("iam_id", sa.Integer(), nullable=True),
        sa.Column("uid", sa.Integer(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("rd_username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("is_alert", sa.Boolean(), nullable=True),
        sa.Column("user_type", sa.Integer(), nullable=True),
        sa.Column("storage_used", sa.Float(), nullable=True),
        sa.Column("quit_days", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_rd_username", "users", ["rd_username"], unique=True)

    op.create_table(
        "aggregates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aggregates_id", "aggregates", ["id"], unique=False)
    op.create_index("ix_aggregates_name", "aggregates", ["name"], unique=False)
    op.create_index(
        "ix_aggregates_storage_cluster_id",
        "aggregates",
        ["storage_cluster_id"],
        unique=False,
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("descriptions", sa.Text(), nullable=True),
        sa.Column("is_common", sa.Boolean(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("project_process_code", sa.String(), nullable=True),
        sa.Column("recipients", sa.String(), nullable=True),
        sa.Column("is_alert", sa.Boolean(), nullable=True),
        sa.Column("in_charge_user_id", sa.Integer(), nullable=True),
        sa.Column("pt_user_id", sa.Integer(), nullable=True),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("soft_limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("soft_use_ratio", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["in_charge_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["pt_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_id", "projects", ["id"], unique=False)
    op.create_index("ix_projects_name", "projects", ["name"], unique=True)

    op.create_table(
        "storage_back_up_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source_path", sa.String(), nullable=True),
        sa.Column("destination_path", sa.String(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("process_uid", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_storage_back_up_records_id",
        "storage_back_up_records",
        ["id"],
        unique=False,
    )

    op.create_table(
        "volumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("vserver", sa.String(), nullable=True),
        sa.Column("aggregate", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("soft_limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("soft_use_ratio", sa.Float(), nullable=True),
        sa.Column("allocated", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_volumes_id", "volumes", ["id"], unique=False)
    op.create_index("ix_volumes_name", "volumes", ["name"], unique=False)
    op.create_index(
        "ix_volumes_storage_cluster_id",
        "volumes",
        ["storage_cluster_id"],
        unique=False,
    )

    op.create_table(
        "project_storage_environments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("soft_limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("soft_use_ratio", sa.Float(), nullable=True),
        sa.Column("collection_status", sa.String(length=16), nullable=False),
        sa.Column("last_collected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "collection_status IN ('pending', 'success', 'failed')",
            name="ck_project_storage_environment_collection_status",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_project_storage_environment_project",
        ),
        sa.ForeignKeyConstraint(
            ["storage_cluster_id"],
            ["storage_clusters.id"],
            name="fk_project_storage_environment_cluster",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "name", name="uq_project_storage_environment_project_name"
        ),
        sa.UniqueConstraint(
            "project_id",
            "storage_cluster_id",
            name="uq_project_storage_environment_project_cluster",
        ),
    )
    op.create_index(
        "ix_project_storage_environment_cluster_project",
        "project_storage_environments",
        ["storage_cluster_id", "project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_storage_environment_project_active_id",
        "project_storage_environments",
        ["project_id", "is_active", "id"],
        unique=False,
    )
    op.create_index(
        "ix_project_storage_environment_project_collection_active",
        "project_storage_environments",
        ["project_id", "collection_status", "is_active"],
        unique=False,
    )

    op.create_table(
        "qtrees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=True),
        sa.Column("volume_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("soft_limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("soft_use_ratio", sa.Float(), nullable=True),
        sa.Column("style", sa.String(), nullable=True),
        sa.Column("oplocks", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"]),
        sa.ForeignKeyConstraint(["volume_id"], ["volumes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qtrees_id", "qtrees", ["id"], unique=False)
    op.create_index("ix_qtrees_name", "qtrees", ["name"], unique=False)
    op.create_index(
        "ix_qtrees_storage_cluster_id",
        "qtrees",
        ["storage_cluster_id"],
        unique=False,
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_environment_id", sa.Integer(), nullable=False),
        sa.Column("monitor_host_id", sa.Integer(), nullable=True),
        sa.Column("volume_id", sa.Integer(), nullable=True),
        sa.Column("qtree_id", sa.Integer(), nullable=True),
        sa.Column("in_charge_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("linux_path", sa.String(), nullable=True),
        sa.Column("back_path", sa.String(), nullable=True),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("soft_limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("soft_use_ratio", sa.Float(), nullable=True),
        sa.Column("associated_mail_groups", sa.String(), nullable=True),
        sa.Column("associate_multiple_groups", sa.Boolean(), nullable=True),
        sa.Column("enable_monitoring", sa.Boolean(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=True),
        sa.Column("back_up_enabled", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "enable_monitoring = FALSE OR volume_id IS NOT NULL OR qtree_id IS NOT NULL",
            name="ck_group_monitored_has_storage_target",
        ),
        sa.CheckConstraint(
            "volume_id IS NULL OR qtree_id IS NULL",
            name="ck_group_single_storage_target",
        ),
        sa.ForeignKeyConstraint(
            ["in_charge_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["project_environment_id"],
            ["project_storage_environments.id"],
            name="fk_group_project_storage_environment",
        ),
        sa.ForeignKeyConstraint(["qtree_id"], ["qtrees.id"]),
        sa.ForeignKeyConstraint(
            ["volume_id"], ["volumes.id"], name="fk_group_volume"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_environment_id", "name", name="uq_group_environment_name"
        ),
    )
    op.create_index("ix_groups_id", "groups", ["id"], unique=False)
    op.create_index("ix_groups_linux_path", "groups", ["linux_path"], unique=False)
    op.create_index("ix_groups_name", "groups", ["name"], unique=False)

    op.create_table(
        "large_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("linux_path", sa.String(), nullable=True),
        sa.Column("size", sa.Float(), nullable=True),
        sa.Column("file_type", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_large_files_id", "large_files", ["id"], unique=False)
    op.create_index(
        "ix_large_files_linux_path", "large_files", ["linux_path"], unique=False
    )

    op.create_table(
        "storage_usages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("linux_path", sa.String(), nullable=True),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("soft_limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("soft_use_ratio", sa.Float(), nullable=True),
        sa.Column("file_used", sa.Float(), nullable=True),
        sa.Column("file_limit", sa.Float(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("blocks", sa.Float(), nullable=True),
        sa.Column("io_block", sa.Float(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("device", sa.String(), nullable=True),
        sa.Column("inode", sa.String(), nullable=True),
        sa.Column("links", sa.Integer(), nullable=True),
        sa.Column("access", sa.String(), nullable=True),
        sa.Column("gid", sa.String(), nullable=True),
        sa.Column("access_time", sa.DateTime(), nullable=True),
        sa.Column("modify_time", sa.DateTime(), nullable=True),
        sa.Column("change_time", sa.DateTime(), nullable=True),
        sa.Column("birth_time", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_storage_usages_id", "storage_usages", ["id"], unique=False)
    op.create_index(
        "ix_storage_usages_linux_path",
        "storage_usages",
        ["linux_path"],
        unique=False,
    )
    op.create_index(
        "ix_storage_usages_storage_cluster_id",
        "storage_usages",
        ["storage_cluster_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_storage_usages_storage_cluster_id", table_name="storage_usages")
    op.drop_index("ix_storage_usages_linux_path", table_name="storage_usages")
    op.drop_index("ix_storage_usages_id", table_name="storage_usages")
    op.drop_table("storage_usages")
    op.drop_index("ix_large_files_linux_path", table_name="large_files")
    op.drop_index("ix_large_files_id", table_name="large_files")
    op.drop_table("large_files")
    op.drop_index("ix_groups_name", table_name="groups")
    op.drop_index("ix_groups_linux_path", table_name="groups")
    op.drop_index("ix_groups_id", table_name="groups")
    op.drop_table("groups")
    op.drop_index("ix_qtrees_storage_cluster_id", table_name="qtrees")
    op.drop_index("ix_qtrees_name", table_name="qtrees")
    op.drop_index("ix_qtrees_id", table_name="qtrees")
    op.drop_table("qtrees")
    op.drop_index(
        "ix_project_storage_environment_project_collection_active",
        table_name="project_storage_environments",
    )
    op.drop_index(
        "ix_project_storage_environment_project_active_id",
        table_name="project_storage_environments",
    )
    op.drop_index(
        "ix_project_storage_environment_cluster_project",
        table_name="project_storage_environments",
    )
    op.drop_table("project_storage_environments")
    op.drop_index("ix_volumes_storage_cluster_id", table_name="volumes")
    op.drop_index("ix_volumes_name", table_name="volumes")
    op.drop_index("ix_volumes_id", table_name="volumes")
    op.drop_table("volumes")
    op.drop_index(
        "ix_storage_back_up_records_id", table_name="storage_back_up_records"
    )
    op.drop_table("storage_back_up_records")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_index("ix_projects_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_aggregates_storage_cluster_id", table_name="aggregates")
    op.drop_index("ix_aggregates_name", table_name="aggregates")
    op.drop_index("ix_aggregates_id", table_name="aggregates")
    op.drop_table("aggregates")
    op.drop_index("ix_users_rd_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_storage_conf_id", table_name="storage_conf")
    op.drop_table("storage_conf")
    op.drop_index("ix_storage_clusters_id", table_name="storage_clusters")
    op.drop_table("storage_clusters")
    op.drop_index("ix_storage_alerts_related_type", table_name="storage_alerts")
    op.drop_index("ix_storage_alerts_related_id", table_name="storage_alerts")
    op.drop_index("ix_storage_alerts_id", table_name="storage_alerts")
    op.drop_table("storage_alerts")
    op.drop_index("ix_hosts_id", table_name="hosts")
    op.drop_table("hosts")
