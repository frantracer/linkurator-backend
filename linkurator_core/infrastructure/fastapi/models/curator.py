from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, AnyUrl

from linkurator_core.domain.users.user import User


class CuratorSchema(BaseModel):
    id: UUID
    username: str
    avatar_url: AnyUrl

    @classmethod
    def from_domain_user(cls, user: User) -> CuratorSchema:
        return cls(
            id=user.uuid,
            username=user.username,
            avatar_url=user.avatar_url
        )
