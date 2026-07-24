"""Add rolling Incident correlation state.

Revision ID: 000000000023
Revises: 000000000022
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000023"
down_revision = "000000000022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_correlation_states",
        sa.Column("correlation_key", sa.String(length=512), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("last_evidence_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("correlation_key"),
    )
    op.create_index(
        "ix_incident_correlation_state_incident",
        "incident_correlation_states",
        ["incident_id"],
        unique=False,
    )
    # The rolling cursor becomes authoritative immediately after this revision.
    # Seed it from legacy incidents so the first post-upgrade observation keeps
    # correlating with the latest incident instead of creating a duplicate.
    op.execute(
        sa.text(
            """
            INSERT INTO incident_correlation_states (
                correlation_key,
                incident_id,
                last_evidence_at,
                updated_at
            )
            SELECT
                candidate.correlation_key,
                candidate.id,
                candidate.last_evidence_at,
                candidate.last_evidence_at
            FROM incidents AS candidate
            WHERE NOT EXISTS (
                SELECT 1
                FROM incidents AS newer
                WHERE newer.correlation_key = candidate.correlation_key
                  AND (
                      newer.last_evidence_at > candidate.last_evidence_at
                      OR (
                          newer.last_evidence_at = candidate.last_evidence_at
                          AND newer.id > candidate.id
                      )
                  )
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incident_correlation_state_incident",
        table_name="incident_correlation_states",
    )
    op.drop_table("incident_correlation_states")
