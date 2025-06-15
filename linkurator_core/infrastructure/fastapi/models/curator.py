from __future__ import annotations

from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.users.user import User


class CuratorSchema(BaseModel):
    id: UUID
    username: str
    avatar_url: AnyUrl
    followed: bool

    @classmethod
    def from_domain_user(cls, user: User, followed: bool) -> CuratorSchema:
        return cls(
            id=user.uuid,
            username=str(user.username),
            avatar_url=user.avatar_url,
            followed=followed,
        )
