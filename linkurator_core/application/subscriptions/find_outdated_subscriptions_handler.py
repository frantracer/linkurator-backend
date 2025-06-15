import logging
from datetime import datetime, timedelta, timezone

from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionFilterCriteria,
    SubscriptionRepository,
)

REFRESH_PERIOD_IN_MINUTES = 60 * 24


class FindOutdatedSubscriptionsHandler:
    subscription_repository: SubscriptionRepository
    event_bus: EventBusService

    def __init__(self, subscription_repository: SubscriptionRepository,
                 event_bus: EventBusService) -> None:
        self.subscription_repository = subscription_repository
        self.event_bus = event_bus

    async def handle(self) -> None:
        logging.info("Finding outdated subscriptions")
        now = datetime.now(tz=timezone.utc)
        datetime_limit = now - timedelta(minutes=REFRESH_PERIOD_IN_MINUTES)
        filter_criteria = SubscriptionFilterCriteria(updated_before=datetime_limit)
        outdated_subscriptions = await self.subscription_repository.find(filter_criteria)

        for subscription in outdated_subscriptions:
            logging.info("Found outdated subscription: %s - %s", subscription.uuid, subscription.name)
            await self.event_bus.publish(SubscriptionBecameOutdatedEvent.new(subscription.uuid))
