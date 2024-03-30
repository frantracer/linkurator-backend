import logging
from datetime import datetime, timedelta, timezone

from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.external_service_credential import ExternalServiceType
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository

REFRESH_PERIOD_WITH_NO_SUBSCRIBERS_IN_MINUTES = 60 * 24
REFRESH_PERIOD_WITH_NO_CREDENTIALS_IN_MINUTES = 5
REFRESH_PERIOD_WITH_CREDENTIALS_IN_MINUTES = 1


class FindOutdatedSubscriptionsHandler:
    subscription_repository: SubscriptionRepository
    event_bus: EventBusService

    def __init__(self, subscription_repository: SubscriptionRepository,
                 event_bus: EventBusService,
                 external_credentials_repository: ExternalCredentialRepository,
                 user_repository: UserRepository):
        self.subscription_repository = subscription_repository
        self.event_bus = event_bus
        self.external_credentials_repository = external_credentials_repository
        self.user_repository = user_repository

    async def handle(self) -> None:
        logging.info("Finding outdated subscriptions")
        now = datetime.now(tz=timezone.utc)
        datetime_limit = now - timedelta(minutes=REFRESH_PERIOD_WITH_NO_CREDENTIALS_IN_MINUTES)
        outdated_subscriptions = self.subscription_repository.find_latest_scan_before(datetime_limit)

        for subscription in outdated_subscriptions:
            subscribed_users = self.user_repository.find_users_subscribed_to_subscription(subscription.uuid)
            if len(subscribed_users) == 0:
                continue

            refresh_period = await self.calculate_subscription_refresh_period_in_minutes(subscription)
            if subscription.scanned_at + timedelta(minutes=refresh_period) < now:
                logging.info('Found outdated subscription: %s - %s', subscription.uuid, subscription.name)
                await self.event_bus.publish(SubscriptionBecameOutdatedEvent.new(subscription.uuid))

    async def calculate_subscription_refresh_period_in_minutes(self, subscription: Subscription) -> int:
        subscribed_users = self.user_repository.find_users_subscribed_to_subscription(subscription.uuid)
        if len(subscribed_users) == 0:
            return REFRESH_PERIOD_WITH_NO_SUBSCRIBERS_IN_MINUTES

        user_ids = [user.uuid for user in subscribed_users]
        credentials = await self.external_credentials_repository.find_by_users_and_type(
            user_ids=user_ids, credential_type=ExternalServiceType.YOUTUBE_API_KEY)

        if len(credentials) == 0:
            return REFRESH_PERIOD_WITH_NO_CREDENTIALS_IN_MINUTES

        return REFRESH_PERIOD_WITH_CREDENTIALS_IN_MINUTES
