from __future__ import annotations

from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class ProfileSchema(BaseModel):
    """
    Profile with the user information
    """
    uuid: UUID
    first_name: str
    last_name: str
    email: str
    avatar_url: AnyUrl
    created_at: Iso8601Datetime
    last_scanned_at: Iso8601Datetime
    last_login_at: Iso8601Datetime

    @classmethod
    def from_domain_user(cls, user: User) -> ProfileSchema:
        return cls(
            uuid=user.uuid,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            last_scanned_at=user.scanned_at,
            last_login_at=user.last_login_at,
        )
