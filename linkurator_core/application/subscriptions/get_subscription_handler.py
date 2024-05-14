from uuid import UUID

from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository


class GetSubscriptionHandler:
    def __init__(self, subscription_repository: SubscriptionRepository) -> None:
        self.subscription_repository = subscription_repository

    def handle(self, subscription_id: UUID) -> Subscription:
        subscription = self.subscription_repository.get(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(subscription_id)
        return subscription
