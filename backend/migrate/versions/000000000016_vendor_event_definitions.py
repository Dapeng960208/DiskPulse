"""Create the vendor event association catalog table.

Revision ID: 000000000016
Revises: 000000000015
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000016"
down_revision = "000000000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendor_event_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_type", sa.String(length=32), nullable=False),
        sa.Column("event_code", sa.String(length=255), nullable=False),
        sa.Column("association_type", sa.String(length=32), nullable=False),
        sa.Column("title_zh", sa.String(length=255), nullable=False),
        sa.Column("description_zh", sa.Text(), nullable=False),
        sa.Column("official_reference_url", sa.String(length=1000), nullable=True),
        sa.Column("default_severity", sa.String(length=16), nullable=True),
        sa.Column("version_scope", sa.String(length=255), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "storage_type IN ('netapp', 'isilon')",
            name="ck_vendor_event_definition_storage_type",
        ),
        sa.CheckConstraint(
            "association_type IN ("
            "'fault_log', 'performance_anomaly', 'capacity_threshold', "
            "'system_activity', 'telemetry_degradation', 'unknown'"
            ")",
            name="ck_vendor_event_definition_association_type",
        ),
        sa.CheckConstraint(
            "default_severity IS NULL OR default_severity IN ("
            "'critical', 'error', 'warning', 'info'"
            ")",
            name="ck_vendor_event_definition_default_severity",
        ),
        sa.CheckConstraint(
            "review_status IN ('reviewed', 'pending')",
            name="ck_vendor_event_definition_review_status",
        ),
        sa.CheckConstraint(
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
            "AND trim(version_scope) <> ''"
            ")",
            name="ck_vendor_event_definition_reviewed_evidence",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storage_type",
            "event_code",
            name="uq_vendor_event_definition_storage_code",
        ),
    )
    op.create_index(
        "ix_vendor_event_definition_filters",
        "vendor_event_definitions",
        ["storage_type", "association_type", "review_status"],
    )
    op.create_index(
        "ix_vendor_event_definition_event_code",
        "vendor_event_definitions",
        ["event_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vendor_event_definition_event_code",
        table_name="vendor_event_definitions",
    )
    op.drop_index(
        "ix_vendor_event_definition_filters",
        table_name="vendor_event_definitions",
    )
    op.drop_table("vendor_event_definitions")
