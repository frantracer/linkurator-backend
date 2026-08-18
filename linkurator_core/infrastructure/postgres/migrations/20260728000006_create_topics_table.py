from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE topics (
                uuid UUID PRIMARY KEY,
                name TEXT NOT NULL,
                user_id UUID NOT NULL,
                subscriptions_ids UUID[] NOT NULL DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
        """)
        await conn.execute("CREATE INDEX topics_user_id_idx ON topics (user_id)")
        await conn.execute(
            "CREATE INDEX topics_name_search_idx "
            "ON topics USING GIN (to_tsvector('simple', immutable_unaccent(name)))",
        )
