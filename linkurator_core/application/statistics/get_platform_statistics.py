import asyncio
from dataclasses import dataclass

from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionRepository,
)
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class UserPlatformStatistics:
    registered: int
    active: int


@dataclass
class SubscriptionsPlatformStatistics:
    total: int
    per_provider: dict[str, int]


@dataclass
class ItemsPlatformStatistics:
    total: int
    per_provider: dict[str, int]


@dataclass
class PlatformStatistics:
    users: UserPlatformStatistics
    subscriptions: SubscriptionsPlatformStatistics
    items: ItemsPlatformStatistics


class GetPlatformStatisticsHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        subscription_repository: SubscriptionRepository,
        item_repository: ItemRepository,
        subscription_services: list[SubscriptionService],
    ) -> None:
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.subscription_services = subscription_services

    async def handle(self) -> PlatformStatistics:
        provider_names = [service.provider_name() for service in self.subscription_services]

        user_results = await asyncio.gather(
            self.user_repository.count_registered_users(),
            self.user_repository.count_active_users(),
        )

        subscription_counts = await asyncio.gather(
            *[self.subscription_repository.count_subscriptions(provider=provider) for provider in provider_names],
        )

        item_counts = await asyncio.gather(
            *[self.item_repository.count_items(provider=provider) for provider in provider_names],
        )

        subscriptions_per_provider = dict(zip(provider_names, subscription_counts))
        items_per_provider = dict(zip(provider_names, item_counts))

        return PlatformStatistics(
            users=UserPlatformStatistics(registered=user_results[0], active=user_results[1]),
            subscriptions=SubscriptionsPlatformStatistics(
                total=sum(subscription_counts),
                per_provider=subscriptions_per_provider,
            ),
            items=ItemsPlatformStatistics(
                total=sum(item_counts),
                per_provider=items_per_provider,
            ),
        )
