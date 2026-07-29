from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        # unaccent() itself is only STABLE, so it can't be used in an index expression.
        # Wrap it in an IMMUTABLE function (safe: the unaccent dictionary is fixed at migration time).
        await conn.execute("""
            CREATE OR REPLACE FUNCTION immutable_unaccent(text)
            RETURNS text AS $$
                SELECT unaccent('unaccent', $1)
            $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        """)
