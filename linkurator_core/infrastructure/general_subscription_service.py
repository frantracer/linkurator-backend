import asyncio
import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import AnyUrl

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential
from linkurator_core.infrastructure.google.youtube_service import YoutubeService
from linkurator_core.infrastructure.spotify.spotify_service import SpotifySubscriptionService


class GeneralSubscriptionService(SubscriptionService):
    def __init__(self,
                 spotify_service: SpotifySubscriptionService,
                 youtube_service: YoutubeService):
        self.spotify_service = spotify_service
        self.youtube_service = youtube_service

    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Subscription]:
        results = await asyncio.gather(
            self.spotify_service.get_subscriptions(user_id, credential),
            self.youtube_service.get_subscriptions(user_id, credential)
        )
        return results[0] + results[1]

    async def get_subscription(
            self,
            sub_id: uuid.UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> Optional[Subscription]:
        results = await asyncio.gather(
            self.spotify_service.get_subscription(sub_id, credential),
            self.youtube_service.get_subscription(sub_id, credential)
        )

        return results[0] or results[1]

    async def get_items(
            self,
            item_ids: set[uuid.UUID],
            credential: Optional[ExternalServiceCredential] = None
    ) -> set[Item]:
        results = await asyncio.gather(
            self.spotify_service.get_items(item_ids, credential),
            self.youtube_service.get_items(item_ids, credential)
        )

        return results[0] | results[1]

    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Item]:
        results = await asyncio.gather(
            self.spotify_service.get_subscription_items(sub_id, from_date, credential),
            self.youtube_service.get_subscription_items(sub_id, from_date, credential)
        )

        return results[0] + results[1]

    async def get_subscription_from_url(
            self,
            url: AnyUrl,
            credential: Optional[ExternalServiceCredential] = None
    ) -> Subscription | None:
        results = await asyncio.gather(
            self.spotify_service.get_subscription_from_url(url, credential),
            self.youtube_service.get_subscription_from_url(url, credential)
        )

        return results[0] or results[1]

    async def get_subscriptions_from_name(
            self,
            name: str,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Subscription]:
        results = await asyncio.gather(
            self.spotify_service.get_subscriptions_from_name(name, credential),
            self.youtube_service.get_subscriptions_from_name(name, credential)
        )

        return results[0] + results[1]
