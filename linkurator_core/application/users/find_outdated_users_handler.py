from datetime import datetime, timedelta, timezone

from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.users.user_repository import UserRepository


class FindOutdatedUsersHandler:
    def __init__(self, user_repository: UserRepository, event_bus: EventBusService) -> None:
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def handle(self) -> None:
        datetime_limit = datetime.now(tz=timezone.utc) - timedelta(days=1)
        outdated_users = await self.user_repository.find_latest_scan_before(datetime_limit)

        for user in outdated_users:
            print(f'Found outdated user: {user.uuid}')
            await self.event_bus.publish(UserSubscriptionsBecameOutdatedEvent.new(user.uuid))
