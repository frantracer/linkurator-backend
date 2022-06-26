from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.user import User


class ProfileSchema(BaseModel):
    """
    Profile with the user information
    """
    uuid: UUID
    first_name: str
    last_name: str
    email: str
    avatar_url: AnyUrl
    created_at: datetime
    last_scanned_at: datetime
    last_login_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        }

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
