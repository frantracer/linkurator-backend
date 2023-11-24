from linkurator_core.application.items.refresh_items_handler import RefreshItemsHandler
from linkurator_core.application.subscriptions.update_subscription_items_handler import UpdateSubscriptionItemsHandler
from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent, UserSubscriptionsBecameOutdatedEvent, \
    ItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import Event


class EventHandler:
    def __init__(self,
                 update_user_subscriptions_handler: UpdateUserSubscriptionsHandler,
                 update_subscription_items_handler: UpdateSubscriptionItemsHandler,
                 refresh_items_handler: RefreshItemsHandler):
        self.update_user_subscriptions_handler = update_user_subscriptions_handler
        self.update_subscription_items_handler = update_subscription_items_handler
        self.refresh_items_handler = refresh_items_handler

    async def handle(self, event: Event) -> None:
        if isinstance(event, UserSubscriptionsBecameOutdatedEvent):
            await self.update_user_subscriptions_handler.handle(event.user_id)
        elif isinstance(event, SubscriptionBecameOutdatedEvent):
            await self.update_subscription_items_handler.handle(event.subscription_id)
        elif isinstance(event, ItemsBecameOutdatedEvent):
            await self.refresh_items_handler.handle(event.item_ids)
        else:
            print(f'Unhandled event: {event}')
