from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository


class FindSubscriptionsByNameHandler:
    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    async def handle(self, name: str) -> list[Subscription]:
        return await self.subscription_repository.find_by_name(name)
