from uuid import UUID

from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, UserNotFoundError
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository


class RefreshSubscriptionHandler:
    def __init__(self,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 subscription_service: SubscriptionService):
        self._user_repository = user_repository
        self._subscription_repository = subscription_repository
        self._subscription_service = subscription_service

    async def handle(self, user_id: UUID, subscription_id: UUID):
        user = self._user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError("No user found")

        if subscription_id not in user.subscription_uuids:
            raise PermissionError("User is not subscribed to this subscription")

        updated_sub = await self._subscription_service.get_subscription(subscription_id)
        if updated_sub is None:
            raise SubscriptionNotFoundError("No subscription found")

        self._subscription_repository.update(updated_sub)
