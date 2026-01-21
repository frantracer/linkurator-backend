from uuid import UUID

from linkurator_core.domain.common.event import SubscriptionNeedsSummarizationEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.types import DateGenerator
from linkurator_core.domain.common.utils import datetime_now
from linkurator_core.domain.subscriptions.general_subscription_service import GeneralSubscriptionService
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository


class UpdateSubscriptionHandler:
    def __init__(self,
                 subscription_repository: SubscriptionRepository,
                 subscription_service: GeneralSubscriptionService,
                 event_bus: EventBusService,
                 date_generator: DateGenerator = datetime_now,
                 ) -> None:
        self.subscription_repository = subscription_repository
        self.subscription_service = subscription_service
        self.event_bus = event_bus
        self.date_generator = date_generator

    async def handle(self, subscription_id: UUID) -> None:
        current_sub = await self.subscription_repository.get(subscription_id)
        if current_sub is None:
            return

        updated_sub = await self.subscription_service.get_subscription(subscription_id)
        if updated_sub is None:
            return

        updated_sub.updated_at = self.date_generator()
        await self.subscription_repository.update(updated_sub)

        if current_sub.description != updated_sub.description:
            await self.event_bus.publish(SubscriptionNeedsSummarizationEvent.new(subscription_id))
