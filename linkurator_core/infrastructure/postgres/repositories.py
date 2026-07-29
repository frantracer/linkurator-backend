from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import re
from ipaddress import IPv4Address

import psycopg

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration

MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"
MIGRATION_FILENAME_PATTERN = re.compile(r"^(\d{14})_\w+\.py$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

MAINTENANCE_DATABASE = "postgres"
ADVISORY_LOCK_KEY = "linkurator_schema_migrations"


def run_postgres_migrations(address: IPv4Address, port: int, db_name: str, user: str, password: str) -> None:
    asyncio.run(_run_migrations(address, port, db_name, user, password))


async def _run_migrations(address: IPv4Address, port: int, db_name: str, user: str, password: str) -> None:
    if not IDENTIFIER_PATTERN.match(db_name):
        msg = f"Invalid database name: {db_name}"
        raise ValueError(msg)

    await _ensure_database_exists(address, port, db_name, user, password)

    conn = await psycopg.AsyncConnection.connect(
        host=str(address), port=port, dbname=db_name, user=user, password=password,
    )
    try:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (ADVISORY_LOCK_KEY,))
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            applied_cursor = await conn.execute("SELECT version FROM schema_migrations")
            applied_versions = {row[0] for row in await applied_cursor.fetchall()}

            for migration_path in _sorted_migration_files():
                match = MIGRATION_FILENAME_PATTERN.match(migration_path.name)
                if match is None:
                    continue
                version = match.group(1)
                if version in applied_versions:
                    continue

                migration = _load_migration(migration_path)
                await migration.upgrade(conn)
                await conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
    finally:
        await conn.close()


async def _ensure_database_exists(
        address: IPv4Address, port: int, db_name: str, user: str, password: str,
) -> None:
    conn = await psycopg.AsyncConnection.connect(
        host=str(address), port=port, dbname=MAINTENANCE_DATABASE, user=user, password=password,
        autocommit=True,
    )
    try:
        cursor = await conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = await cursor.fetchone()
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


def _sorted_migration_files() -> list[pathlib.Path]:
    return sorted(MIGRATIONS_DIR.glob("*.py"), key=lambda path: path.name)


def _load_migration(path: pathlib.Path) -> BaseMigration:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        msg = f"Could not load migration file: {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    migration_class: type[BaseMigration] = module.Migration
    return migration_class()
