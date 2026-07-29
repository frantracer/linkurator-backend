from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE password_change_requests (
                uuid UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                valid_until TIMESTAMPTZ NOT NULL,
                validation_base_url TEXT NOT NULL
            )
        """)
