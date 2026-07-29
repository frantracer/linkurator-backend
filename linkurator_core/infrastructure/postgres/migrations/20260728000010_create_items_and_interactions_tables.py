from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE items (
                uuid UUID PRIMARY KEY,
                subscription_uuid UUID NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnail TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                published_at TIMESTAMPTZ NOT NULL,
                provider TEXT NOT NULL,
                deleted_at TIMESTAMPTZ,
                duration INTEGER,
                version INTEGER NOT NULL DEFAULT 0
            )
        """)
        await conn.execute("CREATE INDEX items_url_idx ON items (url)")
        await conn.execute(
            "CREATE INDEX items_deleted_provider_version_duration_idx "
            "ON items (deleted_at, provider, version, duration)",
        )
        await conn.execute(
            "CREATE INDEX items_subscription_deleted_published_duration_idx "
            "ON items (subscription_uuid, deleted_at, published_at, duration)",
        )
        await conn.execute(
            "CREATE INDEX items_name_search_idx "
            "ON items USING GIN (to_tsvector('simple', immutable_unaccent(name)))",
        )

        await conn.execute("""
            CREATE TABLE interactions (
                uuid UUID PRIMARY KEY,
                item_uuid UUID NOT NULL,
                user_uuid UUID NOT NULL,
                type TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            )
        """)
        await conn.execute("CREATE INDEX interactions_item_user_type_idx ON interactions (item_uuid, user_uuid, type)")
        await conn.execute("CREATE INDEX interactions_user_type_idx ON interactions (user_uuid, type)")
        await conn.execute("CREATE INDEX interactions_created_at_idx ON interactions (created_at DESC)")
