from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

from linkurator_core.domain.chats.chat import Chat, ChatMessage, ChatRole
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector


def _row_to_message(row: Any) -> ChatMessage:
    return ChatMessage(
        role=ChatRole(row["role"]),
        content=row["content"],
        timestamp=row["timestamp"],
        item_uuids=list(row["item_uuids"]),
        subscription_uuids=list(row["subscription_uuids"]),
        topic_uuids=list(row["topic_uuids"]),
        topic_were_created=row["topic_were_created"],
    )


def _row_to_chat(chat_row: Any, message_rows: list[Any]) -> Chat:
    return Chat(
        uuid=chat_row["uuid"],
        user_id=chat_row["user_id"],
        title=chat_row["title"],
        messages=[_row_to_message(row) for row in message_rows],
        created_at=chat_row["created_at"],
        updated_at=chat_row["updated_at"],
    )


def _drop_nul_bytes(value: str) -> str:
    """
    Postgres text columns cannot store a NUL (0x00) byte. Stray NUL bytes occasionally show
    up in LLM-generated or user-pasted content and would otherwise crash the insert, so they
    are dropped rather than treated as meaningful content.
    """
    return value.replace("\x00", "") if "\x00" in value else value


async def _insert_messages(conn: Any, chat_id: UUID, messages: list[ChatMessage]) -> None:
    if len(messages) == 0:
        return
    await conn.executemany(
        """
        INSERT INTO chat_messages (
            chat_id, seq, role, content, timestamp,
            item_uuids, subscription_uuids, topic_uuids, topic_were_created
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                chat_id, seq, message.role.value, _drop_nul_bytes(message.content), message.timestamp,
                message.item_uuids, message.subscription_uuids, message.topic_uuids,
                message.topic_were_created,
            )
            for seq, message in enumerate(messages)
        ],
    )


class PostgresChatRepository(ChatRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def add(self, chat: Chat) -> None:
        pool = await self._connector.pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                INSERT INTO chats (uuid, user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                chat.uuid, chat.user_id, _drop_nul_bytes(chat.title), chat.created_at, chat.updated_at,
            )
            await _insert_messages(conn, chat.uuid, chat.messages)

    async def get(self, chat_id: UUID) -> Chat | None:
        pool = await self._connector.pool()
        chat_row = await pool.fetchrow("SELECT * FROM chats WHERE uuid = %s", chat_id)
        if chat_row is None:
            return None
        message_rows = await pool.fetch(
            "SELECT * FROM chat_messages WHERE chat_id = %s ORDER BY seq", chat_id,
        )
        return _row_to_chat(chat_row, message_rows)

    async def get_by_user_id(self, user_id: UUID) -> list[Chat]:
        pool = await self._connector.pool()
        chat_rows = await pool.fetch(
            "SELECT * FROM chats WHERE user_id = %s ORDER BY updated_at DESC", user_id,
        )
        chats = []
        for chat_row in chat_rows:
            message_rows = await pool.fetch(
                "SELECT * FROM chat_messages WHERE chat_id = %s ORDER BY seq", chat_row["uuid"],
            )
            chats.append(_row_to_chat(chat_row, message_rows))
        return chats

    async def update(self, chat: Chat) -> None:
        pool = await self._connector.pool()
        async with pool.acquire() as conn, conn.transaction():
            result = await conn.execute(
                "UPDATE chats SET user_id = %s, title = %s, updated_at = %s WHERE uuid = %s",
                chat.user_id, _drop_nul_bytes(chat.title), chat.updated_at, chat.uuid,
            )
            if result == "UPDATE 0":
                return
            await conn.execute("DELETE FROM chat_messages WHERE chat_id = %s", chat.uuid)
            await _insert_messages(conn, chat.uuid, chat.messages)

    async def delete(self, chat_id: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM chats WHERE uuid = %s", chat_id)

    async def delete_all(self) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM chats")
