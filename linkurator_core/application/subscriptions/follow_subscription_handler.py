from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class FollowSubscriptionHandler:
    def __init__(self, subscription_repository: SubscriptionRepository, user_repository: UserRepository):
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository

    async def handle(self, user_id: UUID, subscription_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        user.follow_subscription(subscription_id)

        await self.user_repository.update(user)
