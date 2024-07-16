from random import random
from typing import Optional
from uuid import UUID

from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, UserNotFoundError
from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceType, ExternalServiceCredential
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository


class RefreshSubscriptionHandler:
    def __init__(self,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 subscription_service: SubscriptionService,
                 credentials_repository: ExternalCredentialRepository):
        self._user_repository = user_repository
        self._subscription_repository = subscription_repository
        self._subscription_service = subscription_service
        self._credentials_repository = credentials_repository

    async def handle(self, user_id: UUID, subscription_id: UUID) -> None:
        user = await self._user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError("No user found")

        if subscription_id not in user.subscription_uuids:
            raise PermissionError("User is not subscribed to this subscription")

        subscription = self._subscription_repository.get(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError("No subscription found")

        credential: Optional[ExternalServiceCredential] = None
        credential_type = self.map_subscription_provider_to_credential_type(subscription.provider)
        if credential_type is not None:
            related_credentials = await self._credentials_repository.find_by_users_and_type(
                user_ids=[user_id], credential_type=credential_type)
            if len(related_credentials) > 0:
                random_index = int(random() * len(related_credentials))
                credential = related_credentials[random_index]
            if credential is None:
                raise PermissionError("User has no credentials for this subscription")

        updated_sub = await self._subscription_service.get_subscription(sub_id=subscription_id, credential=credential)
        if updated_sub is None:
            raise SubscriptionNotFoundError("No subscription found")

        self._subscription_repository.update(updated_sub)

    @staticmethod
    def map_subscription_provider_to_credential_type(provider: SubscriptionProvider) -> Optional[ExternalServiceType]:
        if provider == SubscriptionProvider.YOUTUBE:
            return ExternalServiceType.YOUTUBE_API_KEY
        return None
