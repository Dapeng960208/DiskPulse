# -*- coding: utf-8 -*-
import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from questdb.database import questdb_engine


MIGRATION_ROOT = Path(__file__).with_name("migrations")
VERSION_TABLE = "diskpulse_schema_migrations"
VERSION_PATTERN = re.compile(r"^(?P<version>\d{12})_(?P<name>[a-z0-9_]+)\.sql$")
CREATE_VERSION_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {VERSION_TABLE} (
    version SYMBOL,
    checksum SYMBOL,
    applied_at TIMESTAMP
) TIMESTAMP(applied_at) PARTITION BY YEAR WAL
"""


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    checksum: str
    statements: tuple[str, ...]


def _split_statements(source: str) -> tuple[str, ...]:
    # ponytail: QuestDB migrations are plain DDL; add a SQL parser only if literals need semicolons.
    return tuple(statement.strip() for statement in source.split(";") if statement.strip())


def load_migrations(path: Path = MIGRATION_ROOT) -> tuple[Migration, ...]:
    migrations = []
    versions = set()
    for migration_path in sorted(path.glob("*.sql")):
        match = VERSION_PATTERN.fullmatch(migration_path.name)
        if match is None:
            raise RuntimeError(f"Invalid QuestDB migration filename: {migration_path.name}")
        version = match.group("version")
        if version in versions:
            raise RuntimeError(f"Duplicate QuestDB migration version: {version}")
        versions.add(version)
        source = migration_path.read_text(encoding="utf-8")
        migrations.append(
            Migration(
                version=version,
                name=match.group("name"),
                checksum=hashlib.sha256(source.encode("utf-8")).hexdigest(),
                statements=_split_statements(source),
            )
        )
    return tuple(migrations)


def _applied_migrations(connection) -> dict[str, str]:
    rows = connection.execute(
        text(f"SELECT version, checksum FROM {VERSION_TABLE} ORDER BY applied_at")
    ).all()
    applied = {}
    for version, checksum in rows:
        version = str(version)
        checksum = str(checksum)
        if version in applied and applied[version] != checksum:
            raise RuntimeError(f"QuestDB migration {version} has conflicting checksums")
        applied[version] = checksum
    return applied


def upgrade(engine=questdb_engine) -> tuple[str, ...]:
    migrations = load_migrations()
    local = {migration.version: migration for migration in migrations}
    upgraded = []

    with engine.connect() as connection:
        connection.execute(text(CREATE_VERSION_TABLE_SQL))
        applied = _applied_migrations(connection)
        unknown = sorted(set(applied) - set(local))
        if unknown:
            raise RuntimeError(f"Unknown applied QuestDB migrations: {', '.join(unknown)}")

        for migration in migrations:
            checksum = applied.get(migration.version)
            if checksum is not None:
                if checksum != migration.checksum:
                    raise RuntimeError(
                        f"QuestDB migration {migration.version} checksum mismatch"
                    )
                continue
            for statement in migration.statements:
                connection.execute(text(statement))
            connection.execute(
                text(
                    f"INSERT INTO {VERSION_TABLE} "
                    "(version, checksum, applied_at) VALUES (:version, :checksum, now())"
                ),
                {"version": migration.version, "checksum": migration.checksum},
            )
            upgraded.append(migration.version)
        connection.commit()

    return tuple(upgraded)


def current(engine=questdb_engine) -> tuple[str, ...]:
    with engine.connect() as connection:
        tables = set(connection.execute(text("SELECT table_name FROM tables()")).scalars())
        if VERSION_TABLE not in tables:
            return ()
        return tuple(_applied_migrations(connection))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage DiskPulse QuestDB migrations")
    parser.add_argument("command", choices=("current", "history", "upgrade"))
    args = parser.parse_args(argv)

    if args.command == "history":
        for migration in load_migrations():
            print(f"{migration.version} {migration.name}")
    elif args.command == "current":
        versions = current()
        print(versions[-1] if versions else "base")
    else:
        versions = upgrade()
        print(f"upgraded: {', '.join(versions)}" if versions else "up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
