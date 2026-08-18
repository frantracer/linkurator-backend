from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE chats (
                uuid UUID PRIMARY KEY,
                user_id UUID,
                title TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
        """)
        await conn.execute("CREATE INDEX chats_user_id_updated_at_idx ON chats (user_id, updated_at DESC)")

        await conn.execute("""
            CREATE TABLE chat_messages (
                id BIGSERIAL PRIMARY KEY,
                chat_id UUID NOT NULL REFERENCES chats (uuid) ON DELETE CASCADE,
                seq INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                item_uuids UUID[] NOT NULL DEFAULT '{}',
                subscription_uuids UUID[] NOT NULL DEFAULT '{}',
                topic_uuids UUID[] NOT NULL DEFAULT '{}',
                topic_were_created BOOLEAN NOT NULL DEFAULT FALSE,
                UNIQUE (chat_id, seq)
            )
        """)
