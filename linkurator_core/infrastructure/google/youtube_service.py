from __future__ import annotations

import uuid
from datetime import datetime
from random import randint
from typing import Dict, List, Optional

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import InvalidCredentialTypeError, InvalidCredentialError
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceType, ExternalServiceCredential
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient
from linkurator_core.infrastructure.google.youtube_rss_client import YoutubeRssClient


class YoutubeService(SubscriptionService):
    def __init__(self, google_account_service: GoogleAccountService,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository,
                 credentials_repository: ExternalCredentialRepository,
                 youtube_client: YoutubeApiClient,
                 youtube_rss_client: YoutubeRssClient,
                 api_keys: list[str]):
        self.google_account_service = google_account_service
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.credentials_repository = credentials_repository
        self.youtube_client = youtube_client
        self.youtube_rss_client = youtube_rss_client
        self.api_keys = api_keys

        if len(api_keys) == 0:
            raise ValueError("No API keys provided")

    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Subscription]:
        """
        Get subscriptions for a user from YouTube.

        :param user_id: user id
        :param credential: credential to use for the request
        :return: list of subscriptions

        :raises InvalidCredentialTypeError: if the credential type is not YOUTUBE_API_KEY
        :raises InvalidCredentialError: if the user refresh token is invalid
        """

        user = await self.user_repository.get(user_id)
        youtube_channels = []

        api_key = self._get_api_key()
        if credential is not None:
            if not credential.credential_type == ExternalServiceType.YOUTUBE_API_KEY:
                raise InvalidCredentialTypeError("Invalid credential type")
            api_key = credential.credential_value

        if user is not None and user.google_refresh_token is not None:
            access_token = self.google_account_service.generate_access_token_from_refresh_token(
                user.google_refresh_token)

            if access_token is None:
                raise InvalidCredentialError("Invalid refresh token")

            channels = await self.youtube_client.get_youtube_subscriptions(access_token=access_token,
                                                                           api_key=api_key)
            youtube_channels = [c.to_subscription(sub_id=uuid.uuid4()) for c in channels]

        return youtube_channels

    async def get_subscription(
            self,
            sub_id: uuid.UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> Optional[Subscription]:
        subscription = self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != SubscriptionProvider.YOUTUBE:
            return None

        channel_id = subscription.external_data["channel_id"]

        if credential is not None:
            if not credential.credential_type == ExternalServiceType.YOUTUBE_API_KEY:
                raise InvalidCredentialTypeError("Invalid credential type")
            api_key = credential.credential_value
        else:
            api_key = await self._get_api_key_for_sub(sub_id)

        channel = await self.youtube_client.get_youtube_channel(api_key=api_key, channel_id=channel_id)
        if channel is not None:
            subscription.name = channel.title
            subscription.url = utils.parse_url(channel.url)
            subscription.thumbnail = utils.parse_url(channel.thumbnail_url)
            return subscription
        return None

    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Item]:

        subscription = self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != SubscriptionProvider.YOUTUBE:
            return []

        rss_items = await self.youtube_rss_client.get_youtube_items(
            playlist_id=subscription.external_data["playlist_id"])
        rss_items = [i for i in rss_items if i.published > from_date]
        if len(rss_items) == 0:
            return []

        if credential is not None:
            if not credential.credential_type == ExternalServiceType.YOUTUBE_API_KEY:
                raise InvalidCredentialTypeError("Invalid credential type")
            api_key = credential.credential_value
        else:
            api_key = await self._get_api_key_for_sub(sub_id)

        videos = await self.youtube_client.get_youtube_videos_from_playlist(
            api_key=api_key,
            playlist_id=subscription.external_data["playlist_id"],
            from_date=from_date)

        return [v.to_item(item_id=uuid.uuid4(), sub_id=sub_id) for v in videos]

    async def get_items(
            self,
            item_ids: set[uuid.UUID],
            credential: Optional[ExternalServiceCredential] = None
    ) -> set[Item]:
        def link_to_video_id(link: str) -> str:
            return link.rsplit('/watch?v=', maxsplit=1)[-1]

        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids),
            page_number=0,
            limit=len(item_ids))

        video_id_to_item: Dict[str, Item] = {link_to_video_id(str(item.url)): item for item in items}

        updated_videos = await self.youtube_client.get_youtube_videos(
            api_key=self._get_api_key() if credential is None else credential.credential_value,
            video_ids=[link_to_video_id(str(item.url)) for item in items])

        updated_items = {v.to_item(item_id=video_id_to_item[v.video_id].uuid,
                                   sub_id=video_id_to_item[v.video_id].subscription_uuid)
                         for v in updated_videos}

        return updated_items

    async def _get_api_key_for_sub(self, sub_id: uuid.UUID) -> str:
        subscribed_users = await self.user_repository.find_users_subscribed_to_subscription(sub_id)
        if len(subscribed_users) == 0:
            return self._get_api_key()

        credentials = await self.credentials_repository.find_by_users_and_type(
            user_ids=[u.uuid for u in subscribed_users],
            credential_type=ExternalServiceType.YOUTUBE_API_KEY
        )

        if len(credentials) == 0:
            return self._get_api_key()

        return credentials[randint(0, len(credentials) - 1)].credential_value

    def _get_api_key(self) -> str:
        return self.api_keys[randint(0, len(self.api_keys) - 1)]
