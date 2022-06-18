import datetime
import uuid

from linkurator_core.application.event_bus_service import EventBusService
from linkurator_core.domain.event import SubscriptionBecameOutdatedEvent
from linkurator_core.domain.subscription_repository import SubscriptionRepository


class FindOutdatedSubscriptionsHandler:
    subscription_repository: SubscriptionRepository
    event_bus: EventBusService

    def __init__(self, subscription_repository: SubscriptionRepository, event_bus: EventBusService):
        self.subscription_repository = subscription_repository
        self.event_bus = event_bus

    def handle(self):
        datetime_limit = datetime.datetime.now() - datetime.timedelta(days=1)
        outdated_subscriptions = self.subscription_repository.find_latest_scan_before(datetime_limit)

        for subscription in outdated_subscriptions:
            print(f'Found outdated subscription: {subscription.uuid}')
            self.event_bus.publish(SubscriptionBecameOutdatedEvent(uuid.uuid4(), subscription.uuid))
