import uuid
from datetime import datetime, timezone

from linkurator_core.domain.common.event import SubscriptionNeedsSummarizationEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import InvalidCredentialError
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository


class UpdateYoutubeUserSubscriptionsHandler:
    def __init__(self,
                 youtube_subscription_service: SubscriptionService,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 event_bus_service: EventBusService) -> None:
        self.subscription_service = youtube_subscription_service
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository
        self.event_bus_service = event_bus_service

    async def handle(self, user_id: uuid.UUID, access_token: str) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            return

        try:
            subscriptions = await self.subscription_service.get_subscriptions(
                user_id=user_id, access_token=access_token)
            updated_subscriptions = [await self._get_or_create_subscription(subscription)
                                     for subscription in subscriptions]
            user.set_youtube_subscriptions({subscription.uuid for subscription in updated_subscriptions})
        except InvalidCredentialError:
            pass

        user.scanned_at = datetime.now(timezone.utc)
        await self.user_repository.update(user)

    async def _get_or_create_subscription(self, subscription: Subscription) -> Subscription:
        registered_subscription = await self.subscription_repository.find_by_url(subscription.url)
        if registered_subscription is None:
            await self.subscription_repository.add(subscription)
            # Publish event for new subscription that needs summarization
            event = SubscriptionNeedsSummarizationEvent.new(subscription.uuid)
            await self.event_bus_service.publish(event)
            return subscription
        return registered_subscription
