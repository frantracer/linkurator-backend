from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.users.account_service import AccountService
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository

RegistrationError = str


class RegisterUserHandler:
    def __init__(self, user_repository: UserRepository,
                 account_service: AccountService,
                 event_bus: EventBusService):
        self.user_repository = user_repository
        self.account_service = account_service
        self.event_bus = event_bus

    async def handle(self, access_token: str, refresh_token: Optional[str]) -> Optional[RegistrationError]:
        user_info = self.account_service.get_user_info(access_token)
        if user_info is None or user_info.details is None:
            return "Failed to get user info"

        user = await self.user_repository.get_by_email(user_info.email)
        if user is None:
            if refresh_token is None:
                return "Refresh token is required for new users"

            user = User.new(
                uuid=uuid4(),
                email=user_info.email,
                avatar_url=user_info.details.picture,
                locale=user_info.details.locale,
                first_name=user_info.details.given_name,
                last_name=user_info.details.family_name,
                google_refresh_token=refresh_token)
            await self.user_repository.add(user)

        else:
            user.avatar_url = user_info.details.picture
            user.locale = user_info.details.locale
            user.first_name = user_info.details.given_name
            user.last_name = user_info.details.family_name
            if refresh_token is not None:
                user.google_refresh_token = refresh_token

            now = datetime.now(timezone.utc)
            user.updated_at = now
            user.last_login_at = now
            await self.user_repository.update(user)

        await self.event_bus.publish(UserSubscriptionsBecameOutdatedEvent.new(user_id=user.uuid))

        return None
