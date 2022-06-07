from linkurator_core.domain.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.application.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.application.event_bus_service import Event


class EventHandler:
    def __init__(self, update_user_subscriptions_handler: UpdateUserSubscriptionsHandler):
        self.update_user_subscriptions_handler = update_user_subscriptions_handler

    def handle(self, event: Event):
        if isinstance(event, UserSubscriptionsBecameOutdatedEvent):
            self.update_user_subscriptions_handler.handle(event.user_id)
