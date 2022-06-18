from linkurator_core.application.event_bus_service import Event
from linkurator_core.application.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.event import UserSubscriptionsBecameOutdatedEvent


class EventHandler:
    def __init__(self, update_user_subscriptions_handler: UpdateUserSubscriptionsHandler):
        self.update_user_subscriptions_handler = update_user_subscriptions_handler

    async def handle(self, event: Event) -> None:
        if isinstance(event, UserSubscriptionsBecameOutdatedEvent):
            await self.update_user_subscriptions_handler.handle(event.user_id)
        else:
            print(f'Unhandled event: {event}')
