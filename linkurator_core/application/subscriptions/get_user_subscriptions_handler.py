from datetime import datetime
from uuid import UUID

from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class GetUserSubscriptionsHandler:
    def __init__(self, subscription_repository: SubscriptionRepository, user_repository: UserRepository) -> None:
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository

    async def handle(self,
               user_id: UUID,
               page_number: int,
               page_size: int,
               created_before: datetime
               ) -> list[Subscription]:
        user = self.user_repository.get(user_id)
        if user is None:
            return []

        user_subscriptions = self.subscription_repository.get_list(user.subscription_uuids)

        filtered_subscriptions = [
            sub for sub in user_subscriptions
            if sub.created_at.timestamp() < created_before.timestamp()
        ]

        start_index = page_number * page_size
        end_index = min(start_index + page_size, len(filtered_subscriptions))

        return filtered_subscriptions[start_index:end_index]
