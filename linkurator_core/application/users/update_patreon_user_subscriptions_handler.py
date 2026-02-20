import logging
import uuid

from linkurator_core.domain.common.event import SubscriptionNeedsSummarizationEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository


class UpdatePatreonUserSubscriptionsHandler:
    def __init__(
        self,
        patreon_subscription_service: SubscriptionService,
        user_repository: UserRepository,
        subscription_repository: SubscriptionRepository,
        event_bus_service: EventBusService,
    ) -> None:
        self.subscription_service = patreon_subscription_service
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository
        self.event_bus_service = event_bus_service

    async def handle(self, user_id: uuid.UUID, access_token: str) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            return

        try:
            subscriptions = await self.subscription_service.get_subscriptions(
                user_id=user_id,
                access_token=access_token,
            )
            for subscription in subscriptions:
                registered = await self._get_or_create_subscription(subscription)
                user.follow_subscription(registered.uuid)

            await self.user_repository.update(user)

        except Exception as e:
            logging.exception("Failed to update Patreon subscriptions for user %s: %s", user_id, e)

    async def _get_or_create_subscription(self, subscription: Subscription) -> Subscription:
        registered_subscription = await self.subscription_repository.find_by_url(subscription.url)
        if registered_subscription is None:
            await self.subscription_repository.add(subscription)
            event = SubscriptionNeedsSummarizationEvent.new(subscription.uuid)
            await self.event_bus_service.publish(event)
            return subscription
        return registered_subscription
