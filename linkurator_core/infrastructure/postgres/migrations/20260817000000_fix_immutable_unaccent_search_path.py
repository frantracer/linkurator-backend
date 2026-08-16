from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        # pg_dump/pg_restore always run with search_path set to '' for restore safety, so
        # both the unqualified unaccent() call and the 'unaccent' dictionary name literal
        # (also resolved via search_path when cast to regdictionary) fail to resolve when
        # this function is inlined during a post-restore CREATE INDEX. Schema-qualify both
        # so dumps restore cleanly regardless of the session's search_path.
        await conn.execute("""
            CREATE OR REPLACE FUNCTION immutable_unaccent(text)
            RETURNS text AS $$
                SELECT public.unaccent('public.unaccent', $1)
            $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        """)
