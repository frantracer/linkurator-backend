from datetime import datetime
import uuid

from linkurator_core.domain.subscription import Subscription
from linkurator_core.application.subscription_service import SubscriptionService
from linkurator_core.domain.subscription_repository import SubscriptionRepository
from linkurator_core.domain.user_repository import UserRepository


class UpdateUserSubscriptionsHandler:
    def __init__(self,
                 subscription_service: SubscriptionService,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository):
        self.subscription_service = subscription_service
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository

    def handle(self, user_id: uuid.UUID) -> None:
        user = self.user_repository.get(user_id)
        if user is None:
            print(f"Cannot update subscriptions for user with id {user_id}: user not found")
            return

        subscriptions = self.subscription_service.get_subscriptions(user_id)

        updated_subscriptions = [self._get_or_create_subscription(subscription) for subscription in subscriptions]

        user.subscription_uuids = [subscription.uuid for subscription in updated_subscriptions]
        user.scanned_at = datetime.now()
        self.user_repository.update(user)

    def _get_or_create_subscription(self, subscription: Subscription) -> Subscription:
        registered_subscription = self.subscription_repository.find(subscription)
        if registered_subscription is None:
            self.subscription_repository.add(subscription)
            return subscription
        return registered_subscription