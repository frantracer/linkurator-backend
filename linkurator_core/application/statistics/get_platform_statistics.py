import asyncio
from dataclasses import dataclass

from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionRepository,
)
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class UserPlatformStatistics:
    registered: int
    active: int


@dataclass
class SubscriptionsPlatformStatistics:
    total: int
    youtube: int
    spotify: int


@dataclass
class ItemsPlatformStatistics:
    total: int
    youtube: int
    spotify: int


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
    ) -> None:
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository

    async def handle(self) -> PlatformStatistics:
        # TODO: Count per provider must be dynamic based on available providers
        results = await asyncio.gather(
            self.user_repository.count_registered_users(),
            self.user_repository.count_active_users(),
            self.subscription_repository.count_subscriptions(
                provider="youtube",
            ),
            self.subscription_repository.count_subscriptions(
                provider="spotify",
            ),
            self.item_repository.count_items(
                provider="youtube",
            ),
            self.item_repository.count_items(
                provider="spotify",
            ),
        )

        return PlatformStatistics(
            users=UserPlatformStatistics(registered=results[0], active=results[1]),
            subscriptions=SubscriptionsPlatformStatistics(
                total=results[2] + results[3], youtube=results[2], spotify=results[3],
            ),
            items=ItemsPlatformStatistics(
                total=results[4] + results[5], youtube=results[4], spotify=results[5],
            ),
        )
