import asyncio
from dataclasses import dataclass

from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider
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
class PlatformStatistics:
    users: UserPlatformStatistics
    subscriptions: SubscriptionsPlatformStatistics


class GetPlatformStatisticsHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        subscription_repository: SubscriptionRepository,
    ):
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository

    async def handle(self) -> PlatformStatistics:
        results = await asyncio.gather(
            self.user_repository.count_registered_users(),
            self.user_repository.count_active_users(),
            self.subscription_repository.count_subscriptions(
                provider=SubscriptionProvider.YOUTUBE
            ),
            self.subscription_repository.count_subscriptions(
                provider=SubscriptionProvider.SPOTIFY
            ),
        )

        return PlatformStatistics(
            users=UserPlatformStatistics(registered=results[0], active=results[1]),
            subscriptions=SubscriptionsPlatformStatistics(
                total=results[2] + results[3], youtube=results[2], spotify=results[3]
            ),
        )
