from dataclasses import dataclass

from linkurator_core.application.auth.send_validate_new_user_email import (
    SendValidateNewUserEmail,
)
from linkurator_core.application.auth.send_welcome_email import SendWelcomeEmail
from linkurator_core.application.chats.process_user_query_handler import ProcessUserQueryHandler
from linkurator_core.application.items.refresh_items_handler import RefreshItemsHandler
from linkurator_core.application.subscriptions.update_subscription_handler import UpdateSubscriptionHandler
from linkurator_core.application.subscriptions.update_subscription_items_handler import (
    UpdateSubscriptionItemsHandler,
)
from linkurator_core.application.users.update_user_subscriptions_handler import (
    UpdateUserSubscriptionsHandler,
)
from linkurator_core.domain.common.event import (
    Event,
    ItemsBecameOutdatedEvent,
    NewChatQueryEvent,
    SubscriptionBecameOutdatedEvent,
    SubscriptionItemsBecameOutdatedEvent,
    UserRegisteredEvent,
    UserRegisterRequestSentEvent,
)


@dataclass
class EventHandler:
    update_user_subscriptions_handler: UpdateUserSubscriptionsHandler
    update_subscription_items_handler: UpdateSubscriptionItemsHandler
    update_subscription_handler: UpdateSubscriptionHandler
    refresh_items_handler: RefreshItemsHandler
    send_validate_new_user_email: SendValidateNewUserEmail
    send_welcome_email: SendWelcomeEmail
    process_user_query_handler: ProcessUserQueryHandler

    async def handle(self, event: Event) -> None:
        if isinstance(event, SubscriptionItemsBecameOutdatedEvent):
            await self.update_subscription_items_handler.handle(event.subscription_id)
        elif isinstance(event, SubscriptionBecameOutdatedEvent):
            await self.update_subscription_handler.handle(event.subscription_id)
        elif isinstance(event, ItemsBecameOutdatedEvent):
            await self.refresh_items_handler.handle(event.item_ids)
        elif isinstance(event, UserRegisterRequestSentEvent):
            await self.send_validate_new_user_email.handle(event.request_uuid)
        elif isinstance(event, UserRegisteredEvent):
            await self.send_welcome_email.handle(event.user_id)
        elif isinstance(event, NewChatQueryEvent):
            await self.process_user_query_handler.handle(event.chat_id, event.query)
        else:
            pass
