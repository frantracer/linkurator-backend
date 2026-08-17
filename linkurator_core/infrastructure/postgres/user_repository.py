from __future__ import annotations

import datetime
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

import psycopg

from linkurator_core.domain.common import utils
from linkurator_core.domain.users.user import HashedPassword, User, Username
from linkurator_core.domain.users.user_repository import EmailAlreadyInUse, UserRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector

INSERT_COLUMNS = """
    uuid, first_name, last_name, username, email, avatar_url, locale,
    created_at, updated_at, scanned_at, last_login_at, google_refresh_token,
    password_hash, password_salt, subscription_uuids, youtube_subscription_uuids,
    youtube_unfollowed_subscription_uuids, followed_topics, favorite_topics,
    is_admin, curators
"""
INSERT_PLACEHOLDERS = ", ".join(["%s"] * 21)


def _row_to_domain(row: Any) -> User:
    password_hash = None
    if row["password_hash"] is not None:
        password_hash = HashedPassword(
            hashed_pass_plus_salt=row["password_hash"],
            salt=row["password_salt"],
        )
    return User(
        uuid=row["uuid"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        username=Username(row["username"]),
        email=row["email"],
        avatar_url=utils.parse_url(row["avatar_url"]),
        locale=row["locale"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        scanned_at=row["scanned_at"],
        last_login_at=row["last_login_at"],
        google_refresh_token=row["google_refresh_token"],
        password_hash=password_hash,
        _subscription_uuids=set(row["subscription_uuids"]),
        _youtube_subscriptions_uuids=set(row["youtube_subscription_uuids"]),
        _unfollowed_youtube_subscriptions_uuids=set(row["youtube_unfollowed_subscription_uuids"]),
        _followed_topics=set(row["followed_topics"]),
        _favorite_topics=set(row["favorite_topics"]),
        is_admin=row["is_admin"],
        curators=set(row["curators"]),
    )


def user_params(user: User) -> tuple[Any, ...]:
    password_hash = None if user.password_hash is None else user.password_hash.hashed_pass_plus_salt
    password_salt = None if user.password_hash is None else user.password_hash.salt
    return (
        user.uuid, user.first_name, user.last_name, str(user.username), user.email,
        str(user.avatar_url), user.locale, user.created_at, user.updated_at,
        user.scanned_at, user.last_login_at, user.google_refresh_token,
        password_hash, password_salt,
        list(user.get_subscriptions(include_youtube=False)),
        list(user.get_youtube_subscriptions()),
        list(user.get_youtube_unfollowed_subscriptions()),
        list(user.get_followed_topics()),
        list(user.get_favorite_topics()),
        user.is_admin,
        list(user.curators),
    )


class PostgresUserRepository(UserRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def add(self, user: User) -> None:
        pool = await self._connector.pool()
        try:
            await pool.execute(
                f"INSERT INTO users ({INSERT_COLUMNS}) VALUES ({INSERT_PLACEHOLDERS})",  # noqa: S608
                *user_params(user),
            )
        except psycopg.errors.UniqueViolation as error:
            if error.diag.constraint_name == "users_email_key":
                msg = f"Email '{user.email}' is already in use"
                raise EmailAlreadyInUse(msg) from error
            # A username collision is silently swallowed here: only the email uniqueness
            # violation is translated into a domain exception.

    async def get(self, user_id: UUID) -> User | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM users WHERE uuid = %s", user_id)
        return None if row is None else _row_to_domain(row)

    async def get_all(self) -> list[User]:
        pool = await self._connector.pool()
        rows = await pool.fetch("SELECT * FROM users")
        return [_row_to_domain(row) for row in rows]

    async def get_by_email(self, email: str) -> User | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM users WHERE email = %s", email)
        return None if row is None else _row_to_domain(row)

    async def get_by_username(self, username: Username) -> User | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM users WHERE username = %s", str(username))
        return None if row is None else _row_to_domain(row)

    async def delete(self, user_id: UUID) -> None:
        pool = await self._connector.pool()
        async with pool.acquire() as conn, conn.transaction():
            result = await conn.execute(
                f"""
                INSERT INTO deleted_users ({INSERT_COLUMNS}, deleted_at)
                SELECT {INSERT_COLUMNS}, now() FROM users WHERE uuid = %s
                """,  # noqa: S608
                user_id,
            )
            if result == "INSERT 0 0":
                return
            await conn.execute("DELETE FROM users WHERE uuid = %s", user_id)

    async def delete_all(self) -> None:
        pool = await self._connector.pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                f"INSERT INTO deleted_users ({INSERT_COLUMNS}, deleted_at) "  # noqa: S608
                f"SELECT {INSERT_COLUMNS}, now() FROM users",
            )
            await conn.execute("DELETE FROM users")

    async def update(self, user: User) -> None:
        pool = await self._connector.pool()
        uuid_param, *rest = user_params(user)
        await pool.execute(
            """
            UPDATE users SET
                first_name = %s, last_name = %s, username = %s, email = %s, avatar_url = %s, locale = %s,
                created_at = %s, updated_at = %s, scanned_at = %s, last_login_at = %s,
                google_refresh_token = %s, password_hash = %s, password_salt = %s,
                subscription_uuids = %s, youtube_subscription_uuids = %s,
                youtube_unfollowed_subscription_uuids = %s, followed_topics = %s, favorite_topics = %s,
                is_admin = %s, curators = %s
            WHERE uuid = %s
            """,
            *rest, uuid_param,
        )

    async def find_latest_scan_before(self, timestamp: datetime.datetime) -> list[User]:
        pool = await self._connector.pool()
        rows = await pool.fetch("SELECT * FROM users WHERE scanned_at < %s", timestamp)
        return [_row_to_domain(row) for row in rows]

    async def find_users_subscribed_to_subscription(self, subscription_id: UUID) -> list[User]:
        pool = await self._connector.pool()
        rows = await pool.fetch(
            """
            SELECT * FROM users
            WHERE %s = ANY(subscription_uuids) OR %s = ANY(youtube_subscription_uuids)
            """,
            subscription_id, subscription_id,
        )
        return [_row_to_domain(row) for row in rows]

    async def count_registered_users(self) -> int:
        pool = await self._connector.pool()
        return await pool.fetchval("SELECT COUNT(*) FROM users")

    async def count_active_users(self) -> int:
        pool = await self._connector.pool()
        logged_after = User.time_since_last_active()
        return await pool.fetchval("SELECT COUNT(*) FROM users WHERE last_login_at > %s", logged_after)

    async def search_by_username(self, username_part: str) -> list[User]:
        pool = await self._connector.pool()
        rows = await pool.fetch(
            "SELECT * FROM users WHERE username ILIKE '%%' || %s || '%%'", username_part,
        )
        return [_row_to_domain(row) for row in rows]
