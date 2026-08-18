from __future__ import annotations

from ipaddress import IPv4Address

import psycopg

from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector


class TokenAlreadyExists(Exception):
    pass


class PostgresSessionRepository(SessionRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def get(self, token: str) -> Session | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM sessions WHERE token = %s", token)
        if row is None:
            return None
        return Session(token=row["token"], user_id=row["user_id"], expires_at=row["expires_at"])

    async def add(self, session: Session) -> None:
        pool = await self._connector.pool()
        try:
            await pool.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
                session.token, session.user_id, session.expires_at,
            )
        except psycopg.errors.UniqueViolation as error:
            msg = f"Token '{session.token}' already exists"
            raise TokenAlreadyExists(msg) from error

    async def delete(self, token: str) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM sessions WHERE token = %s", token)
