from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

import psycopg

from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector


def _row_to_domain(row: Any) -> Topic:
    return Topic(
        uuid=row["uuid"],
        name=row["name"],
        user_id=row["user_id"],
        subscriptions_ids=list(row["subscriptions_ids"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresTopicRepository(TopicRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def add(self, topic: Topic) -> None:
        pool = await self._connector.pool()
        try:
            await pool.execute(
                """
                INSERT INTO topics (uuid, name, user_id, subscriptions_ids, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                topic.uuid, topic.name, topic.user_id, topic.subscriptions_ids,
                topic.created_at, topic.updated_at,
            )
        except psycopg.errors.UniqueViolation as error:
            msg = f"Topic with id '{topic.uuid}' already exists"
            raise DuplicatedKeyError(msg) from error

    async def get(self, topic_id: UUID) -> Topic | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM topics WHERE uuid = %s", topic_id)
        return None if row is None else _row_to_domain(row)

    async def find_topics(self, topic_ids: list[UUID]) -> list[Topic]:
        pool = await self._connector.pool()
        rows = await pool.fetch("SELECT * FROM topics WHERE uuid = ANY(%s::uuid[])", topic_ids)
        return [_row_to_domain(row) for row in rows]

    async def find_topics_by_name(self, name: str) -> list[Topic]:
        pool = await self._connector.pool()
        rows = await pool.fetch(
            """
            SELECT * FROM topics
            WHERE to_tsvector('simple', immutable_unaccent(name))
                @@ plainto_tsquery('simple', immutable_unaccent(%s))
            ORDER BY created_at DESC
            """,
            name,
        )
        return [_row_to_domain(row) for row in rows]

    async def update(self, topic: Topic) -> None:
        pool = await self._connector.pool()
        await pool.execute(
            """
            UPDATE topics
            SET name = %s, user_id = %s, subscriptions_ids = %s, updated_at = %s
            WHERE uuid = %s
            """,
            topic.name, topic.user_id, topic.subscriptions_ids, topic.updated_at, topic.uuid,
        )

    async def delete(self, topic_id: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM topics WHERE uuid = %s", topic_id)

    async def delete_all(self) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM topics")

    async def get_by_user_id(self, user_id: UUID) -> list[Topic]:
        pool = await self._connector.pool()
        rows = await pool.fetch("SELECT * FROM topics WHERE user_id = %s", user_id)
        return [_row_to_domain(row) for row in rows]
