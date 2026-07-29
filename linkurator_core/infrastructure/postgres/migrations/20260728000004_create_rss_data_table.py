from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE rss_data (
                id BIGSERIAL PRIMARY KEY,
                rss_url TEXT NOT NULL,
                item_url TEXT NOT NULL,
                raw_data TEXT NOT NULL,
                UNIQUE (rss_url, item_url)
            )
        """)
