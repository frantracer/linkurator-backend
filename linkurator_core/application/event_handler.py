from linkurator_core.application.event_bus_service import Event
from linkurator_core.application.update_subscription_items_handler import UpdateSubscriptionItemsHandler
from linkurator_core.application.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.event import SubscriptionBecameOutdatedEvent, UserSubscriptionsBecameOutdatedEvent


class EventHandler:
    def __init__(self,
                 update_user_subscriptions_handler: UpdateUserSubscriptionsHandler,
                 update_subscription_items_handler: UpdateSubscriptionItemsHandler):
        self.update_user_subscriptions_handler = update_user_subscriptions_handler
        self.update_subscription_items_handler = update_subscription_items_handler

    async def handle(self, event: Event) -> None:
        if isinstance(event, UserSubscriptionsBecameOutdatedEvent):
            await self.update_user_subscriptions_handler.handle(event.user_id)
        elif isinstance(event, SubscriptionBecameOutdatedEvent):
            await self.update_subscription_items_handler.handle(event.subscription_id)
        else:
            print(f'Unhandled event: {event}')
