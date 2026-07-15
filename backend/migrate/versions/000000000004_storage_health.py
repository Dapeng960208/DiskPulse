"""Add storage health event fields and indexes.

Revision ID: 000000000004
Revises: 000000000003
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000004"
down_revision: str = "000000000003"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    with op.batch_alter_table("storage_alerts") as batch_op:
        batch_op.add_column(sa.Column("storage_cluster_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "source",
                sa.String(32),
                nullable=False,
                server_default="diskpulse",
            )
        )
        batch_op.add_column(sa.Column("external_event_id", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("fingerprint", sa.String(512), nullable=True))
        batch_op.add_column(
            sa.Column("severity", sa.String(16), nullable=False, server_default="info")
        )
        batch_op.create_foreign_key(
            "fk_storage_alert_cluster",
            "storage_clusters",
            ["storage_cluster_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_storage_alert_vendor_event",
            ["storage_cluster_id", "source", "external_event_id"],
        )

    alerts = sa.table(
        "storage_alerts",
        sa.column("alert_level", sa.String()),
        sa.column("severity", sa.String()),
        sa.column("related_id", sa.Integer()),
        sa.column("related_type", sa.String()),
        sa.column("storage_cluster_id", sa.Integer()),
    )
    op.execute(
        alerts.update().values(
            severity=sa.case(
                (alerts.c.alert_level == "high", "critical"),
                (alerts.c.alert_level == "medium", "warning"),
                (alerts.c.alert_level == "low", "info"),
                else_="info",
            )
        )
    )

    # Existing project-level alerts can span clusters and intentionally remain NULL.
    for related_type, table_name in (
        ("Group", "groups"),
        ("StorageUsage", "storage_usages"),
        ("Volume", "volumes"),
        ("Qtree", "qtrees"),
        ("Aggregate", "aggregates"),
    ):
        resource = sa.table(
            table_name,
            sa.column("id", sa.Integer()),
            sa.column("storage_cluster_id", sa.Integer()),
        )
        op.execute(
            alerts.update()
            .where(alerts.c.related_type == related_type)
            .values(
                storage_cluster_id=sa.select(resource.c.storage_cluster_id)
                .where(resource.c.id == alerts.c.related_id)
                .scalar_subquery()
            )
        )

    op.create_index(
        "ix_storage_alert_cluster_updated",
        "storage_alerts",
        ["storage_cluster_id", "updated_at"],
    )
    op.create_index(
        "ix_storage_alert_severity_updated",
        "storage_alerts",
        ["severity", "updated_at"],
    )
    op.create_index(
        "ix_storage_alert_fingerprint_updated",
        "storage_alerts",
        ["fingerprint", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_storage_alert_fingerprint_updated", table_name="storage_alerts")
    op.drop_index("ix_storage_alert_severity_updated", table_name="storage_alerts")
    op.drop_index("ix_storage_alert_cluster_updated", table_name="storage_alerts")
    with op.batch_alter_table("storage_alerts") as batch_op:
        batch_op.drop_constraint("uq_storage_alert_vendor_event", type_="unique")
        batch_op.drop_constraint("fk_storage_alert_cluster", type_="foreignkey")
        batch_op.drop_column("severity")
        batch_op.drop_column("fingerprint")
        batch_op.drop_column("external_event_id")
        batch_op.drop_column("source")
        batch_op.drop_column("storage_cluster_id")
