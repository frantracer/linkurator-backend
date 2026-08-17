from __future__ import annotations

import atexit
from ipaddress import IPv4Address
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.session_repository import SessionRepository


class TokenAlreadyExists(Exception):
    pass


class PostgresSessionRepository(SessionRepository):
    """Uses a synchronous driver (psycopg3), since sessions are read on the hot request path."""

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._pool: ConnectionPool[psycopg.Connection[dict[str, Any]]] = ConnectionPool(
            conninfo="",
            min_size=1,
            max_size=10,
            kwargs={
                "host": str(ip), "port": port, "dbname": db_name, "user": username, "password": password,
                "autocommit": True, "row_factory": dict_row,
            },
        )
        # The pool's background workers are plain threads; without an explicit close() they
        # only stop via a best-effort GC-time join, which can stall interpreter shutdown by
        # several seconds per worker.
        atexit.register(self._pool.close)

    def get(self, token: str) -> Session | None:
        with self._pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT * FROM sessions WHERE token = %s", (token,))
            row = cursor.fetchone()
        if row is None:
            return None
        return Session(token=row["token"], user_id=row["user_id"], expires_at=row["expires_at"])

    def add(self, session: Session) -> None:
        try:
            with self._pool.connection() as conn, conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
                    (session.token, session.user_id, session.expires_at),
                )
        except psycopg.errors.UniqueViolation as error:
            msg = f"Token '{session.token}' already exists"
            raise TokenAlreadyExists(msg) from error

    def delete(self, token: str) -> None:
        with self._pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute("DELETE FROM sessions WHERE token = %s", (token,))
