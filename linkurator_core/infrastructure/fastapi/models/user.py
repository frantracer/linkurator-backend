from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from linkurator_core.domain.users.user import User


class UserSchema(BaseModel):
    id: UUID
    username: str

    @classmethod
    def from_domain_user(cls, user: User) -> UserSchema:
        return cls(
            id=user.uuid,
            username=user.username
        )
