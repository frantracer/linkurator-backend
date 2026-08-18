from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE user_filters (
                user_id UUID PRIMARY KEY,
                text_filter TEXT,
                min_duration INTEGER,
                max_duration INTEGER,
                include_items_without_interactions BOOLEAN NOT NULL,
                include_recommended_items BOOLEAN NOT NULL,
                include_discouraged_items BOOLEAN NOT NULL,
                include_viewed_items BOOLEAN NOT NULL,
                include_hidden_items BOOLEAN NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
        """)
