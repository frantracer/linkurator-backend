import datetime
from copy import copy
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.users.user import User, Username
from linkurator_core.domain.users.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        super().__init__()
        self.users: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self.users[user.uuid] = user

    async def get(self, user_id: UUID) -> Optional[User]:
        return copy(self.users.get(user_id))

    async def get_by_email(self, email: str) -> Optional[User]:
        for user in self.users.values():
            if user.email == email:
                return copy(user)
        return None

    async def get_by_username(self, username: Username) -> Optional[User]:
        for user in self.users.values():
            if user.username == username:
                return copy(user)
        return None

    async def delete(self, user_id: UUID) -> None:
        if user_id in self.users:
            del self.users[user_id]

    async def update(self, user: User) -> None:
        self.users[user.uuid] = user

    async def find_latest_scan_before(self, timestamp: datetime.datetime) -> List[User]:
        found_users = []
        for user in self.users.values():
            if user.scanned_at < timestamp:
                found_users.append(copy(user))

        return found_users

    async def find_users_subscribed_to_subscription(self, subscription_id: UUID) -> List[User]:
        found_users = []
        for user in self.users.values():
            if subscription_id in user.get_subscriptions():
                found_users.append(copy(user))

        return found_users
