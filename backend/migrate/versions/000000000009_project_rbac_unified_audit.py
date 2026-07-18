"""Add project RBAC and immutable unified audit events.

Revision ID: 000000000009
Revises: 000000000008
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000009"
down_revision: str = "000000000008"
branch_labels: None = None
depends_on: None = None


def _dialect_name() -> str:
    return op.get_context().dialect.name


def _sqlite_projects_table(*, include_pt_user: bool) -> sa.Table:
    """Return the revision-007 projects shape for offline SQLite batch DDL."""
    metadata = sa.MetaData()
    columns = [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("descriptions", sa.Text(), nullable=True),
        sa.Column("is_common", sa.Boolean(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("project_process_code", sa.String(), nullable=True),
        sa.Column("recipients", sa.String(), nullable=True),
        sa.Column("is_alert", sa.Boolean(), nullable=True),
        sa.Column("storage_alert_rule", sa.JSON(), nullable=True),
        sa.Column("in_charge_user_id", sa.Integer(), nullable=True),
    ]
    if include_pt_user:
        columns.append(sa.Column("pt_user_id", sa.Integer(), nullable=True))
    columns.extend(
        [
            sa.Column("limit", sa.Float(), nullable=True),
            sa.Column("soft_limit", sa.Float(), nullable=True),
            sa.Column("used", sa.Float(), nullable=True),
            sa.Column("use_ratio", sa.Float(), nullable=True),
            sa.Column("soft_use_ratio", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["in_charge_user_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        ]
    )
    if include_pt_user:
        columns.append(
            sa.ForeignKeyConstraint(["pt_user_id"], ["users.id"], ondelete="SET NULL")
        )
    table = sa.Table("projects", metadata, *columns)
    sa.Index("ix_projects_id", table.c.id)
    sa.Index("ix_projects_name", table.c.name, unique=True)
    return table


def _sqlite_batch_alter_projects(copy_from: sa.Table, alter) -> None:
    """Rebuild projects with foreign-key enforcement safely suspended.

    SQLite cannot replace a parent table while rows in groups still reference
    it. Run the short schema rewrite in Alembic's autocommit block, restore the
    caller's foreign-key setting immediately, and use an explicit copy source
    for offline SQL generation.
    """
    context = op.get_context()
    if context.as_sql:
        op.execute(sa.text("PRAGMA foreign_keys=OFF"))
        with op.batch_alter_table(
            "projects", recreate="always", copy_from=copy_from
        ) as batch_op:
            alter(batch_op)
        op.execute(sa.text("PRAGMA foreign_keys=ON"))
        return

    if context._in_external_transaction:
        raise RuntimeError(
            "SQLite project RBAC migration requires an Alembic-managed connection"
        )

    with context.autocommit_block():
        connection = op.get_bind()
        foreign_keys_enabled = bool(
            connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
        )
        if foreign_keys_enabled:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            with op.batch_alter_table("projects", recreate="always") as batch_op:
                alter(batch_op)
        finally:
            if foreign_keys_enabled:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _mysql_pt_user_fk_names(foreign_keys) -> tuple[str, ...]:
    """Return only the legacy projects.pt_user_id -> users.id constraints."""
    return tuple(
        foreign_key["name"]
        for foreign_key in foreign_keys
        if foreign_key.get("name")
        and foreign_key.get("constrained_columns") == ["pt_user_id"]
        and foreign_key.get("referred_table") == "users"
    )


def _drop_pt_user_column() -> None:
    context = op.get_context()
    if context.dialect.name == "sqlite":
        _sqlite_batch_alter_projects(
            _sqlite_projects_table(include_pt_user=True),
            lambda batch_op: batch_op.drop_column("pt_user_id"),
        )
        return
    if context.dialect.name == "mysql" and not context.as_sql:
        # Review fix: MySQL refuses to drop a column while its legacy FK exists.
        foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys("projects")
        with op.batch_alter_table("projects") as batch_op:
            for foreign_key_name in _mysql_pt_user_fk_names(foreign_keys):
                batch_op.drop_constraint(foreign_key_name, type_="foreignkey")
            batch_op.drop_column("pt_user_id")
        return
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("pt_user_id")


def _restore_pt_user_column() -> None:
    context = op.get_context()
    if context.dialect.name == "sqlite":
        def add_pt_user_column(batch_op) -> None:
            batch_op.add_column(sa.Column("pt_user_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_projects_pt_user_id_users",
                "users",
                ["pt_user_id"],
                ["id"],
                ondelete="SET NULL",
            )

        _sqlite_batch_alter_projects(
            _sqlite_projects_table(include_pt_user=False), add_pt_user_column
        )
        return
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("pt_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_projects_pt_user_id_users",
            "users",
            ["pt_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def _create_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END"
        ))
    elif dialect == "postgresql":
        op.execute(sa.text(
            "CREATE FUNCTION disallow_audit_event_mutation() RETURNS trigger AS $$ "
            "BEGIN RAISE EXCEPTION 'audit_events are append-only'; END; $$ LANGUAGE plpgsql"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events "
            "FOR EACH ROW EXECUTE FUNCTION disallow_audit_event_mutation()"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events "
            "FOR EACH ROW EXECUTE FUNCTION disallow_audit_event_mutation()"
        ))
    elif dialect == "mysql":
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events "
            "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events are append-only'"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events "
            "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events are append-only'"
        ))


def _drop_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_delete ON audit_events"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS disallow_audit_event_mutation()"))
    elif dialect in {"sqlite", "mysql"}:
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_update"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_delete"))


def _create_project_memberships() -> None:
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="reader"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('reader', 'editor', 'project_admin')", name="ck_project_membership_role"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_membership_user"),
    )
    op.create_index("ix_project_membership_user_project", "project_memberships", ["user_id", "project_id"])
    op.create_index("ix_project_membership_project_role", "project_memberships", ["project_id", "role"])


def _backfill_project_owners() -> None:
    context = op.get_context()
    if context.as_sql:
        return
    projects = sa.table(
        "projects",
        sa.column("id", sa.Integer()),
        sa.column("in_charge_user_id", sa.Integer()),
    )
    memberships = sa.table(
        "project_memberships",
        sa.column("project_id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("role", sa.String()),
    )
    rows = op.get_bind().execute(
        sa.select(projects.c.id, projects.c.in_charge_user_id).where(
            projects.c.in_charge_user_id.is_not(None)
        )
    ).all()
    if rows:
        op.get_bind().execute(
            sa.insert(memberships),
            [
                {"project_id": project_id, "user_id": user_id, "role": "project_admin"}
                for project_id, user_id in rows
            ],
        )


def _create_audit_events() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation_id", sa.String(length=36), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        # Historical identities are logical IDs. FK SET NULL would mutate this immutable table.
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column("before_summary", sa.JSON(), nullable=True),
        sa.Column("after_summary", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint("phase IN ('attempt', 'result')", name="ck_audit_event_phase"),
        sa.CheckConstraint("outcome IN ('success', 'denied', 'failure')", name="ck_audit_event_outcome"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_project_occurred_id", "audit_events", ["project_id", "occurred_at", "id"])
    op.create_index("ix_audit_events_actor_occurred_id", "audit_events", ["actor_user_id", "occurred_at", "id"])
    op.create_index("ix_audit_events_operation_occurred", "audit_events", ["operation_id", "occurred_at"])
    _create_immutability_triggers()


def upgrade() -> None:
    # Remove the obsolete FK before creating a table that references projects;
    # this keeps SQLite batch migrations valid when FK enforcement is enabled.
    _drop_pt_user_column()
    _create_project_memberships()
    _backfill_project_owners()
    _create_audit_events()


def downgrade() -> None:
    _drop_immutability_triggers()
    op.drop_index("ix_audit_events_operation_occurred", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_occurred_id", table_name="audit_events")
    op.drop_index("ix_audit_events_project_occurred_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_project_membership_project_role", table_name="project_memberships")
    op.drop_index("ix_project_membership_user_project", table_name="project_memberships")
    op.drop_table("project_memberships")
    _restore_pt_user_column()
