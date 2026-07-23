"""Repair performance analytics derived from legacy QuestDB local timestamps.

Revision ID: 000000000019
Revises: 000000000018

The historical performance writer stored Asia/Shanghai wall-clock values in a
QuestDB connection configured as UTC.  Performance anomaly processing then
treated those values as UTC, moving observations and incident evidence eight
hours into the future.  This migration corrects only the PostgreSQL-derived
performance records.  The raw QuestDB tables are rebuilt separately with
``scripts.repair_questdb_timestamps`` while collectors are stopped.
"""

from alembic import op


revision = "000000000019"
down_revision = "000000000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        r"""
        UPDATE anomaly_observations
        SET source_ref =
                regexp_replace(
                    source_ref,
                    ':[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$',
                    ''
                )
                || ':'
                || to_char(
                    (observed_at - interval '8 hours') AT TIME ZONE 'UTC',
                    'YYYY-MM-DD"T"HH24:MI:SS'
                )
                || '+00:00',
            observed_at = observed_at - interval '8 hours',
            evidence_window_start = evidence_window_start - interval '8 hours',
            evidence_window_end = evidence_window_end - interval '8 hours'
        WHERE source = 'questdb_performance'
        """
    )
    op.execute(
        """
        UPDATE incident_evidence AS evidence
        SET observed_at = evidence.observed_at - interval '8 hours'
        FROM anomaly_observations AS anomaly
        WHERE evidence.source = 'anomaly_observation'
          AND evidence.source_ref = 'anomaly:' || anomaly.id::text
          AND anomaly.source = 'questdb_performance'
        """
    )
    op.execute(
        """
        WITH performance_incident_ids AS (
            SELECT DISTINCT evidence.incident_id
            FROM incident_evidence AS evidence
            JOIN anomaly_observations AS anomaly
              ON evidence.source = 'anomaly_observation'
             AND evidence.source_ref = 'anomaly:' || anomaly.id::text
             AND anomaly.source = 'questdb_performance'
        )
        UPDATE incidents AS incident
        SET correlation_bucket_at =
                TIMESTAMPTZ '1900-01-01 00:00:00+00'
                + incident.id * interval '1 microsecond'
        FROM performance_incident_ids AS targets
        WHERE incident.id = targets.incident_id
          AND incident.category = 'performance_contention'
        """
    )
    op.execute(
        """
        WITH performance_bounds AS (
            SELECT
                evidence.incident_id,
                min(evidence.observed_at) AS first_evidence_at,
                max(evidence.observed_at) AS last_evidence_at
            FROM incident_evidence AS evidence
            JOIN anomaly_observations AS anomaly
              ON evidence.source = 'anomaly_observation'
             AND evidence.source_ref = 'anomaly:' || anomaly.id::text
             AND anomaly.source = 'questdb_performance'
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
        FROM performance_bounds AS bounds
        WHERE incident.id = bounds.incident_id
          AND incident.category = 'performance_contention'
        """
    )


def downgrade() -> None:
    # Intentionally irreversible: after corrected UTC writers start, adding
    # eight hours would corrupt new rows mixed with the repaired history.
    pass
