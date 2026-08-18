from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE registration_requests (
                uuid UUID PRIMARY KEY,
                user_data JSONB NOT NULL,
                valid_until TIMESTAMPTZ NOT NULL,
                validation_base_url TEXT NOT NULL
            )
        """)
