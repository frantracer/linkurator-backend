import asyncio
from dataclasses import dataclass

from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class PlatformStatistics:
    registered_users: int
    active_users: int


class GetPlatformStatisticsHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self) -> PlatformStatistics:
        results = await asyncio.gather(
            self.user_repository.count_registered_users(),
            self.user_repository.count_active_users(),
        )

        return PlatformStatistics(
            registered_users=results[0],
            active_users=results[1],
        )
