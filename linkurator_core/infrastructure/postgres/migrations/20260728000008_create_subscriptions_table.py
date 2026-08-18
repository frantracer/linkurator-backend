from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE subscriptions (
                uuid UUID PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                external_data JSONB NOT NULL DEFAULT '{}',
                url TEXT NOT NULL UNIQUE,
                thumbnail TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                scanned_at TIMESTAMPTZ NOT NULL,
                last_published_at TIMESTAMPTZ NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT ''
            )
        """)
        await conn.execute("CREATE INDEX subscriptions_scanned_at_provider_idx ON subscriptions (scanned_at, provider)")
        await conn.execute("CREATE INDEX subscriptions_updated_at_idx ON subscriptions (updated_at)")
        await conn.execute(
            "CREATE INDEX subscriptions_name_search_idx "
            "ON subscriptions USING GIN (to_tsvector('simple', immutable_unaccent(name)))",
        )
