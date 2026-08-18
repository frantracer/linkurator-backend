from __future__ import annotations

import json
from datetime import datetime
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.common import utils
from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository
from linkurator_core.domain.users.user import HashedPassword, User, Username
from linkurator_core.infrastructure.postgres.common import PostgresConnector


def _user_to_json(user: User) -> dict[str, Any]:
    return {
        "uuid": str(user.uuid),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": str(user.username),
        "email": user.email,
        "avatar_url": str(user.avatar_url),
        "locale": user.locale,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "scanned_at": user.scanned_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat(),
        "google_refresh_token": user.google_refresh_token,
        "is_admin": user.is_admin,
        "subscription_uuids": [str(u) for u in user.get_subscriptions(include_youtube=False)],
        "youtube_subscription_uuids": [str(u) for u in user.get_youtube_subscriptions()],
        "youtube_unfollowed_subscription_uuids": [str(u) for u in user.get_youtube_unfollowed_subscriptions()],
        "followed_topics": [str(u) for u in user.get_followed_topics()],
        "favorite_topics": [str(u) for u in user.get_favorite_topics()],
        "curators": [str(u) for u in user.curators],
        "password_hash": None if user.password_hash is None else {
            "hashed_pass_plus_salt": user.password_hash.hashed_pass_plus_salt,
            "salt": user.password_hash.salt,
        },
    }


def _user_from_json(data: dict[str, Any]) -> User:
    password_hash_data = data["password_hash"]
    return User(
        uuid=UUID(data["uuid"]),
        first_name=data["first_name"],
        last_name=data["last_name"],
        username=Username(data["username"]),
        email=data["email"],
        avatar_url=utils.parse_url(data["avatar_url"]),
        locale=data["locale"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        scanned_at=datetime.fromisoformat(data["scanned_at"]),
        last_login_at=datetime.fromisoformat(data["last_login_at"]),
        google_refresh_token=data["google_refresh_token"],
        is_admin=data["is_admin"],
        _subscription_uuids={UUID(u) for u in data["subscription_uuids"]},
        _youtube_subscriptions_uuids={UUID(u) for u in data["youtube_subscription_uuids"]},
        _unfollowed_youtube_subscriptions_uuids={UUID(u) for u in data["youtube_unfollowed_subscription_uuids"]},
        _followed_topics={UUID(u) for u in data["followed_topics"]},
        _favorite_topics={UUID(u) for u in data["favorite_topics"]},
        curators={UUID(u) for u in data["curators"]},
        password_hash=None if password_hash_data is None else HashedPassword(
            hashed_pass_plus_salt=password_hash_data["hashed_pass_plus_salt"],
            salt=password_hash_data["salt"],
        ),
    )


class PostgresRegistrationRequestRepository(RegistrationRequestRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def add_request(self, request: RegistrationRequest) -> None:
        pool = await self._connector.pool()
        await pool.execute(
            """
            INSERT INTO registration_requests (uuid, user_data, valid_until, validation_base_url)
            VALUES (%s, %s::jsonb, %s, %s)
            """,
            request.uuid,
            json.dumps(_user_to_json(request.user)),
            request.valid_until,
            str(request.validation_base_url),
        )

    async def get_request(self, uuid: UUID) -> RegistrationRequest | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM registration_requests WHERE uuid = %s", uuid)
        if row is None:
            return None
        return RegistrationRequest(
            uuid=row["uuid"],
            user=_user_from_json(row["user_data"]),
            valid_until=row["valid_until"],
            validation_base_url=AnyUrl(row["validation_base_url"]),
        )

    async def delete_request(self, uuid: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM registration_requests WHERE uuid = %s", uuid)
