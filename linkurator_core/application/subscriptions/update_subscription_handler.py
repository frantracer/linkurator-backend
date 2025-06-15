from uuid import UUID

from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


class UpdateSubscriptionHandler:
    def __init__(self,
                 subscription_repository: SubscriptionRepository,
                 subscription_service: SubscriptionService) -> None:
        self.subscription_repository = subscription_repository
        self.subscription_service = subscription_service

    async def handle(self, subscription_id: UUID) -> None:
        updated_sub = await self.subscription_service.get_subscription(subscription_id)
        if updated_sub is not None:
            await self.subscription_repository.update(updated_sub)
