"""Add evidence-backed actions to vendor event definitions.

Revision ID: 000000000017
Revises: 000000000016
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000017"
down_revision = "000000000016"
branch_labels = None
depends_on = None


_PREVIOUS_REVIEWED_EVIDENCE_CHECK = (
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
    ")"
)
_REVIEWED_EVIDENCE_CHECK = (
    _PREVIOUS_REVIEWED_EVIDENCE_CHECK[:-1]
    + " AND recommended_solution_zh IS NOT NULL "
    + "AND trim(recommended_solution_zh) <> ''"
    + ")"
)


def _replace_reviewed_evidence_check(check_sql: str, *, drop_solution: bool) -> None:
    if op.get_context().as_sql:
        op.execute(
            "-- replace ck_vendor_event_definition_reviewed_evidence: " + check_sql
        )
        return
    with op.batch_alter_table("vendor_event_definitions", recreate="always") as batch:
        batch.drop_constraint(
            "ck_vendor_event_definition_reviewed_evidence",
            type_="check",
        )
        batch.create_check_constraint(
            "ck_vendor_event_definition_reviewed_evidence",
            check_sql,
        )
        if drop_solution:
            batch.drop_column("recommended_solution_zh")


def upgrade() -> None:
    op.add_column(
        "vendor_event_definitions",
        sa.Column("recommended_solution_zh", sa.Text(), nullable=True),
    )
    _replace_reviewed_evidence_check(
        _REVIEWED_EVIDENCE_CHECK,
        drop_solution=False,
    )


def downgrade() -> None:
    _replace_reviewed_evidence_check(
        _PREVIOUS_REVIEWED_EVIDENCE_CHECK,
        drop_solution=True,
    )
