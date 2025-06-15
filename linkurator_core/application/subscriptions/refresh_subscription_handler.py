from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

from linkurator_core.domain.common.event import SubscriptionItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import SubscriptionAlreadyUpdatedError, SubscriptionNotFoundError
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService

MIN_REFRESH_INTERVAL_IN_SECONDS = 60 * 60


class RefreshSubscriptionHandler:
    def __init__(
            self,
            subscription_repository: SubscriptionRepository,
            subscription_service: SubscriptionService,
            event_bus: EventBusService,
            datetime_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._subscription_repository = subscription_repository
        self._subscription_service = subscription_service
        self._event_bus = event_bus
        self._datetime_now = datetime_now

    async def handle(self, subscription_id: UUID) -> None:
        now = self._datetime_now()

        subscription = await self._subscription_repository.get(subscription_id)
        if subscription is None:
            msg = "No subscription found"
            raise SubscriptionNotFoundError(msg)

        if now > subscription.scanned_at + timedelta(seconds=MIN_REFRESH_INTERVAL_IN_SECONDS):
            await self._event_bus.publish(SubscriptionItemsBecameOutdatedEvent.new(subscription_id=subscription.uuid))

        if now < subscription.updated_at + timedelta(seconds=MIN_REFRESH_INTERVAL_IN_SECONDS):
            wait_time_in_seconds = (subscription.updated_at + timedelta(
                seconds=MIN_REFRESH_INTERVAL_IN_SECONDS) - now).total_seconds()
            msg = f"Subscription updated too recently. Wait {int(wait_time_in_seconds)} seconds"
            raise SubscriptionAlreadyUpdatedError(
                msg,
            )

        updated_sub = await self._subscription_service.get_subscription(sub_id=subscription_id)
        if updated_sub is None:
            msg = "No subscription found"
            raise SubscriptionNotFoundError(msg)

        updated_sub.updated_at = now

        await self._subscription_repository.update(updated_sub)
