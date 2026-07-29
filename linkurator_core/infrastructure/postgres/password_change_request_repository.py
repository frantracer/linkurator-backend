from __future__ import annotations

from ipaddress import IPv4Address
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.domain.users.password_change_request_repository import PasswordChangeRequestRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector


class PostgresPasswordChangeRequestRepository(PasswordChangeRequestRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def add_request(self, request: PasswordChangeRequest) -> None:
        pool = await self._connector.pool()
        await pool.execute(
            """
            INSERT INTO password_change_requests (uuid, user_id, valid_until, validation_base_url)
            VALUES (%s, %s, %s, %s)
            """,
            request.uuid, request.user_id, request.valid_until, str(request.validation_base_url),
        )

    async def get_request(self, uuid: UUID) -> PasswordChangeRequest | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM password_change_requests WHERE uuid = %s", uuid)
        if row is None:
            return None
        return PasswordChangeRequest(
            uuid=row["uuid"],
            user_id=row["user_id"],
            valid_until=row["valid_until"],
            validation_base_url=AnyUrl(row["validation_base_url"]),
        )

    async def delete_request(self, uuid: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM password_change_requests WHERE uuid = %s", uuid)
