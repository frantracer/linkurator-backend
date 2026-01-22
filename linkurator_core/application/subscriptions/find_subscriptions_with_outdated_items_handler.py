import logging
from datetime import timedelta

from linkurator_core.domain.common.event import SubscriptionItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.session import datetime_now_utc
from linkurator_core.domain.users.user_repository import UserRepository

REFRESH_PERIOD_WITH_NO_SUBSCRIBERS_IN_MINUTES = 60 * 24
REFRESH_PERIOD_WITH_NO_CREDENTIALS_IN_MINUTES = 5


class FindSubscriptionsWithOutdatedItemsHandler:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        event_bus: EventBusService,
        user_repository: UserRepository,
        subscription_services: list[SubscriptionService],
    ) -> None:
        self.subscription_repository = subscription_repository
        self.event_bus = event_bus
        self.user_repository = user_repository
        self.refresh_period_per_provider: dict[str, int] = {
            service.provider_name(): service.refresh_period_minutes()
            for service in subscription_services
        }

    async def handle(self) -> None:
        logging.info("Finding subscriptions with outdated items")
        now = datetime_now_utc()

        for provider, provider_refresh_period in self.refresh_period_per_provider.items():
            datetime_limit = now - timedelta(minutes=provider_refresh_period)
            outdated_subscriptions = await self.subscription_repository.find_latest_scan_before(
                datetime_limit=datetime_limit,
                provider=provider)

            for subscription in outdated_subscriptions:
                sub_refresh_period = await self.calculate_subscription_refresh_period_in_minutes(subscription)
                if subscription.scanned_at + timedelta(minutes=sub_refresh_period) < now:
                    logging.info("Found outdated items for subscription: %s - %s", subscription.uuid, subscription.name)
                    await self.event_bus.publish(SubscriptionItemsBecameOutdatedEvent.new(subscription.uuid))

    async def calculate_subscription_refresh_period_in_minutes(self, subscription: Subscription) -> int:
        subscribed_users = await self.user_repository.find_users_subscribed_to_subscription(subscription.uuid)
        if len(subscribed_users) == 0:
            return REFRESH_PERIOD_WITH_NO_SUBSCRIBERS_IN_MINUTES

        return self.refresh_period_per_provider.get(
            subscription.provider,
            REFRESH_PERIOD_WITH_NO_CREDENTIALS_IN_MINUTES,
        )
