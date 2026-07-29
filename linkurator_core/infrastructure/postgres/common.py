from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from ipaddress import IPv4Address
from typing import Any

from psycopg import AsyncConnection, AsyncTransaction
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

PostgresRow = dict[str, Any]


class PostgresConnection:
    """Thin wrapper around a borrowed psycopg AsyncConnection with asyncpg-style query helpers."""

    def __init__(self, conn: AsyncConnection[PostgresRow]) -> None:
        self._conn = conn

    def transaction(self) -> AbstractAsyncContextManager[AsyncTransaction]:
        return self._conn.transaction()

    async def execute(self, query: str, *args: Any) -> str:
        cursor = await self._conn.execute(query, args)
        return cursor.statusmessage or ""

    async def executemany(self, query: str, args_list: Sequence[Sequence[Any]]) -> None:
        async with self._conn.cursor() as cursor:
            await cursor.executemany(query, args_list)

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        cursor = await self._conn.execute(query, args)
        return await cursor.fetchall()

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        cursor = await self._conn.execute(query, args)
        return await cursor.fetchone()

    async def fetchval(self, query: str, *args: Any) -> Any:
        row = await self.fetchrow(query, *args)
        if row is None:
            return None
        return next(iter(row.values()))

    async def copy_records_to_table(
            self, table: str, records: Sequence[Sequence[Any]], columns: Sequence[str],
    ) -> None:
        columns_sql = ", ".join(columns)
        async with (
            self._conn.cursor() as cursor,
            cursor.copy(f"COPY {table} ({columns_sql}) FROM STDIN") as copy,
        ):
            for record in records:
                await copy.write_row(record)


class PostgresPool:
    """Thin wrapper around a psycopg AsyncConnectionPool with asyncpg-style query helpers."""

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[PostgresRow]]) -> None:
        self._pool = pool

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[PostgresConnection]:
        async with self._pool.connection() as raw_conn:
            yield PostgresConnection(raw_conn)

    async def execute(self, query: str, *args: Any) -> str:
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args_list: Sequence[Sequence[Any]]) -> None:
        async with self.acquire() as conn:
            await conn.executemany(query, args_list)

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)


class PostgresConnector:
    """
    Lazily creates and caches a connection pool for a single (host, db) pair.
    """

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        self._ip = ip
        self._port = port
        self._db_name = db_name
        self._username = username
        self._password = password
        self._pool: PostgresPool | None = None
        self._pool_lock = asyncio.Lock()

    async def pool(self) -> PostgresPool:
        if self._pool is not None:
            return self._pool

        async with self._pool_lock:
            if self._pool is not None:
                return self._pool
            raw_pool: AsyncConnectionPool[AsyncConnection[PostgresRow]] = AsyncConnectionPool(
                conninfo="",
                min_size=1,
                max_size=5,
                open=False,
                kwargs={
                    "host": str(self._ip),
                    "port": self._port,
                    "dbname": self._db_name,
                    "user": self._username,
                    "password": self._password,
                    "autocommit": True,
                    "row_factory": dict_row,
                },
            )
            await raw_pool.open()
            pool = PostgresPool(raw_pool)
            self._pool = pool
            return pool
