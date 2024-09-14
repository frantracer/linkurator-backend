from pydantic import AnyUrl, ValidationError

from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


class FindSubscriptionsByNameOrUrlHandler:
    def __init__(self,
                 subscription_repository: SubscriptionRepository,
                 subscription_service: SubscriptionService,
                 event_bus: EventBusService
                 ):
        self.subscription_repository = subscription_repository
        self.subscription_service = subscription_service
        self.event_bus = event_bus

    async def handle(self, name_or_url: str) -> list[Subscription]:
        url = _try_parse_url(name_or_url)
        if url is None:
            return await self.subscription_repository.find_by_name(name=name_or_url)

        sub = await self.subscription_service.get_subscription_from_url(url)
        if sub is not None:
            existing_sub = await self.subscription_repository.get(sub.uuid)
            if existing_sub is None:
                await self.subscription_repository.add(sub)
                await self.event_bus.publish(SubscriptionBecameOutdatedEvent.new(sub.uuid))
                return  [sub]

            return [existing_sub]

        return []


def _try_parse_url(url: str) -> AnyUrl | None:
    parsed_url: AnyUrl | None = None
    try:
        parsed_url = parse_url(url)
    except ValidationError:
        pass

    return parsed_url
