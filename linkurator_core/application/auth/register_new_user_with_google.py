from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from linkurator_core.domain.common.event import UserRegisteredEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.users.account_service import AccountService
from linkurator_core.domain.users.user import User, Username
from linkurator_core.domain.users.user_repository import UserRepository

RegistrationError = str


class UsernameGenerator(Protocol):
    def generate_username(self) -> Username:
        ...


class UsernameGeneratorFromEmail:
    def __init__(self, email: str) -> None:
        self.email = email

    def generate_username(self) -> Username:
        random_number = str(uuid4().int)[:4]
        email_user = self.email.split("@")[0]
        return Username.transform(f"{email_user}{random_number}")


class RegisterUserHandler:
    def __init__(self, user_repository: UserRepository,
                 account_service: AccountService,
                 event_bus: EventBusService,
                 username_generator: UsernameGenerator | None = None) -> None:
        self.user_repository = user_repository
        self.account_service = account_service
        self.event_bus = event_bus
        self.username_generator = username_generator

    async def handle(self, access_token: str) -> RegistrationError | None:
        user_info = self.account_service.get_user_info(access_token)
        if user_info is None or user_info.details is None:
            return "Failed to get user info"

        user = await self.user_repository.get_by_email(user_info.email)
        if user is None:
            username: Username
            if self.username_generator is None:
                username = UsernameGeneratorFromEmail(
                    user_info.email,
                ).generate_username()
            else:
                username = self.username_generator.generate_username()

            first_name = user_info.details.given_name
            last_name = user_info.details.family_name
            user = User.new(
                uuid=uuid4(),
                email=user_info.email,
                avatar_url=user_info.details.picture,
                locale=user_info.details.locale,
                first_name=first_name,
                last_name=last_name,
                username=username)
            await self.user_repository.add(user)

            await self.event_bus.publish(UserRegisteredEvent.new(user_id=user.uuid))

        else:
            user.avatar_url = user_info.details.picture
            user.locale = user_info.details.locale
            user.first_name = user_info.details.given_name
            user.last_name = user_info.details.family_name

            now = datetime.now(timezone.utc)
            user.updated_at = now
            user.last_login_at = now
            await self.user_repository.update(user)

        return None
