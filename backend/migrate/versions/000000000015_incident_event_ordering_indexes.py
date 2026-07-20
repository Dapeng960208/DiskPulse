"""Index incidents by newest evidence instead of manual update time.

Revision ID: 000000000015
Revises: 000000000014
"""

from alembic import op


revision = "000000000015"
down_revision = "000000000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_incident_project_status_updated", table_name="incidents")
    op.drop_index("ix_incident_cluster_asset_updated", table_name="incidents")
    op.create_index(
        "ix_incident_latest_evidence",
        "incidents",
        ["last_evidence_at", "opened_at", "id"],
    )
    op.create_index(
        "ix_incident_project_status_evidence",
        "incidents",
        ["project_id", "status", "last_evidence_at", "opened_at", "id"],
    )
    op.create_index(
        "ix_incident_cluster_evidence",
        "incidents",
        ["storage_cluster_id", "last_evidence_at", "opened_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_cluster_evidence", table_name="incidents")
    op.drop_index("ix_incident_project_status_evidence", table_name="incidents")
    op.drop_index("ix_incident_latest_evidence", table_name="incidents")
    op.create_index(
        "ix_incident_project_status_updated",
        "incidents",
        ["project_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_incident_cluster_asset_updated",
        "incidents",
        ["storage_cluster_id", "asset_type", "asset_id", "updated_at"],
    )
