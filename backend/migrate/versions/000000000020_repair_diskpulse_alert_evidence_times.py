"""Repair incident times derived from legacy local StorageAlerts timestamps.

Revision ID: 000000000020
Revises: 000000000019

StorageAlerts.updated_at is a legacy timestamp-without-time-zone column whose
values are Asia/Shanghai wall time.  DiskPulse alert evidence previously
treated those naive values as UTC, shifting capacity incidents eight hours
into the future.  The source alert row is authoritative for the repair.
"""

from alembic import op


revision = "000000000020"
down_revision = "000000000019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The repair depends on PostgreSQL time-zone conversion and UPDATE FROM.
    # SQLite structure checks have no legacy PostgreSQL timestamp data to fix.
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        """
        UPDATE incident_evidence AS evidence
        SET observed_at = alert.updated_at AT TIME ZONE 'Asia/Shanghai'
        FROM storage_alerts AS alert
        WHERE evidence.source = 'diskpulse_alert'
          AND evidence.source_ref = 'diskpulse:' || alert.id::text
        """
    )
    op.execute(
        """
        WITH diskpulse_incident_ids AS (
            SELECT DISTINCT evidence.incident_id
            FROM incident_evidence AS evidence
            WHERE evidence.source = 'diskpulse_alert'
        )
        UPDATE incidents AS incident
        SET correlation_bucket_at =
                TIMESTAMPTZ '1900-01-02 00:00:00+00'
                + incident.id * interval '1 microsecond'
        FROM diskpulse_incident_ids AS targets
        WHERE incident.id = targets.incident_id
          AND incident.category = 'capacity_pressure'
        """
    )
    op.execute(
        """
        WITH diskpulse_incident_ids AS (
            SELECT DISTINCT evidence.incident_id
            FROM incident_evidence AS evidence
            WHERE evidence.source = 'diskpulse_alert'
        ),
        evidence_bounds AS (
            SELECT
                evidence.incident_id,
                min(evidence.observed_at) AS first_evidence_at,
                max(evidence.observed_at) AS last_evidence_at
            FROM incident_evidence AS evidence
            JOIN diskpulse_incident_ids AS targets
              ON targets.incident_id = evidence.incident_id
            GROUP BY evidence.incident_id
        )
        UPDATE incidents AS incident
        SET opened_at = bounds.first_evidence_at,
            last_evidence_at = bounds.last_evidence_at,
            correlation_bucket_at =
                date_trunc('hour', bounds.first_evidence_at)
                + (
                    floor(extract(minute FROM bounds.first_evidence_at) / 30)
                    * interval '30 minutes'
                )
        FROM evidence_bounds AS bounds
        WHERE incident.id = bounds.incident_id
          AND incident.category = 'capacity_pressure'
        """
    )


def downgrade() -> None:
    # Irreversible: the source alert wall time has now been interpreted using
    # its documented Asia/Shanghai timezone.
    pass
