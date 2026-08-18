from __future__ import annotations

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from linkurator_core.infrastructure.postgres.migrations.base import BaseMigration


class Migration(BaseMigration):
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        await conn.execute("""
            CREATE TABLE users (
                uuid UUID NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                avatar_url TEXT NOT NULL,
                locale TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                scanned_at TIMESTAMPTZ NOT NULL,
                last_login_at TIMESTAMPTZ NOT NULL,
                google_refresh_token TEXT,
                password_hash TEXT,
                password_salt TEXT,
                subscription_uuids UUID[] NOT NULL DEFAULT '{}',
                youtube_subscription_uuids UUID[] NOT NULL DEFAULT '{}',
                youtube_unfollowed_subscription_uuids UUID[] NOT NULL DEFAULT '{}',
                followed_topics UUID[] NOT NULL DEFAULT '{}',
                favorite_topics UUID[] NOT NULL DEFAULT '{}',
                curators UUID[] NOT NULL DEFAULT '{}',
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                PRIMARY KEY (uuid),
                UNIQUE (username),
                UNIQUE (email)
            )
        """)
        await conn.execute("CREATE INDEX users_scanned_at_idx ON users (scanned_at)")
        await conn.execute("CREATE INDEX users_last_login_at_idx ON users (last_login_at)")
        await conn.execute("CREATE INDEX users_subscription_uuids_idx ON users USING GIN (subscription_uuids)")
        await conn.execute(
            "CREATE INDEX users_youtube_subscription_uuids_idx "
            "ON users USING GIN (youtube_subscription_uuids)",
        )

        # Archive for deleted users (soft-delete-with-move)
        await conn.execute("""
            CREATE TABLE deleted_users (
                id BIGSERIAL PRIMARY KEY,
                uuid UUID NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                avatar_url TEXT NOT NULL,
                locale TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                scanned_at TIMESTAMPTZ NOT NULL,
                last_login_at TIMESTAMPTZ NOT NULL,
                google_refresh_token TEXT,
                password_hash TEXT,
                password_salt TEXT,
                subscription_uuids UUID[] NOT NULL DEFAULT '{}',
                youtube_subscription_uuids UUID[] NOT NULL DEFAULT '{}',
                youtube_unfollowed_subscription_uuids UUID[] NOT NULL DEFAULT '{}',
                followed_topics UUID[] NOT NULL DEFAULT '{}',
                favorite_topics UUID[] NOT NULL DEFAULT '{}',
                curators UUID[] NOT NULL DEFAULT '{}',
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_at TIMESTAMPTZ NOT NULL
            )
        """)
