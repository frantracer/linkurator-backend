import datetime
import uuid

from linkurator_core.domain.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.application.event_bus_service import EventBusService
from linkurator_core.domain.user_repository import UserRepository


class FindOutdatedUsersHandler:
    def __init__(self, user_repository: UserRepository, event_bus: EventBusService):
        self.user_repository = user_repository
        self.event_bus = event_bus

    def handle(self):
        datetime_limit = datetime.datetime.now() - datetime.timedelta(days=1)
        outdated_users = self.user_repository.find_latest_scan_before(datetime_limit)

        for user in outdated_users:
            print(f'Found outdated user: {user.uuid}')
            self.event_bus.publish(UserSubscriptionsBecameOutdatedEvent(uuid.uuid4(), user.uuid))
