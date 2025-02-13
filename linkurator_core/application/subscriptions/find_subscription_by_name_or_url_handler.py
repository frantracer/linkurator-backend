import asyncio

from pydantic import AnyUrl, ValidationError

from linkurator_core.domain.common.event import SubscriptionItemsBecameOutdatedEvent
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
            results = await asyncio.gather(
                self.subscription_repository.find_by_name(name=name_or_url),
                self.subscription_service.get_subscriptions_from_name(name=name_or_url)
            )
            existing_subs = results[0]
            service_subs = results[1]

            existing_subs_uuids = [sub.uuid for sub in existing_subs]
            for service_sub in service_subs:
                if service_sub.uuid not in existing_subs_uuids:
                    existing_service_sub = await self.get_or_create_subscription(service_sub)
                    existing_subs.append(existing_service_sub)

            return existing_subs

        sub = await self.subscription_service.get_subscription_from_url(url)
        if sub is not None:
            return [await self.get_or_create_subscription(sub)]

        return []

    async def get_or_create_subscription(self, sub: Subscription) -> Subscription:
        existing_sub = await self.subscription_repository.get(sub.uuid)
        if existing_sub is None:
            await self.subscription_repository.add(sub)
            await self.event_bus.publish(SubscriptionItemsBecameOutdatedEvent.new(sub.uuid))
            return sub

        return existing_sub


def _try_parse_url(url: str) -> AnyUrl | None:
    parsed_url: AnyUrl | None = None
    try:
        parsed_url = parse_url(url)
    except ValidationError:
        pass

    return parsed_url
