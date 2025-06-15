from __future__ import annotations

from uuid import UUID

from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class GetUserSubscriptionsHandler:
    def __init__(self, subscription_repository: SubscriptionRepository, user_repository: UserRepository) -> None:
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository

    async def handle(self, user_id: UUID) -> list[Subscription]:
        user = await self.user_repository.get(user_id)
        if user is None:
            return []

        return await self.subscription_repository.get_list(list(user.get_subscriptions()))
