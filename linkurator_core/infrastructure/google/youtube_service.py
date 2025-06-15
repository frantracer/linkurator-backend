from __future__ import annotations

import logging
import uuid
from copy import deepcopy
from datetime import datetime
from random import randint

from pydantic import AnyUrl

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import InvalidCredentialTypeError
from linkurator_core.domain.common.utils import datetime_now, parse_url
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient, YoutubeApiError, YoutubeChannel
from linkurator_core.infrastructure.google.youtube_rss_client import YoutubeRssClient


class YoutubeService(SubscriptionService):
    def __init__(self,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository,
                 credentials_repository: ExternalCredentialRepository,
                 youtube_client: YoutubeApiClient,
                 youtube_rss_client: YoutubeRssClient,
                 api_keys: list[str]) -> None:
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.credentials_repository = credentials_repository
        self.youtube_client = youtube_client
        self.youtube_rss_client = youtube_rss_client
        self.api_keys = api_keys

        if len(api_keys) == 0:
            msg = "No API keys provided"
            raise ValueError(msg)

    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            access_token: str,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Subscription]:
        """
        Get subscriptions for a user from YouTube.

        :param user_id: user id
        :param credential: credential to use for the request
        :return: list of subscriptions

        :raises InvalidCredentialTypeError: if the credential type is not YOUTUBE_API_KEY
        """
        user = await self.user_repository.get(user_id)
        youtube_channels = []

        api_key = self._get_api_key()
        if credential is not None:
            if credential.credential_type != ExternalServiceType.YOUTUBE_API_KEY:
                msg = "Invalid credential type"
                raise InvalidCredentialTypeError(msg)
            api_key = credential.credential_value

        if user is not None:
            channels = await self.youtube_client.get_youtube_subscriptions(access_token=access_token,
                                                                           api_key=api_key)
            youtube_channels = [c.to_subscription(sub_id=uuid.uuid4()) for c in channels]

        return youtube_channels

    async def get_subscription(
            self,
            sub_id: uuid.UUID,
            credential: ExternalServiceCredential | None = None,
    ) -> Subscription | None:
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != SubscriptionProvider.YOUTUBE:
            return None

        channel_id = subscription.external_data["channel_id"]

        if credential is not None:
            if credential.credential_type != ExternalServiceType.YOUTUBE_API_KEY:
                msg = "Invalid credential type"
                raise InvalidCredentialTypeError(msg)
            api_key = credential.credential_value
        else:
            api_key = await self._get_api_key_for_sub(sub_id)

        channel = await self.youtube_client.get_youtube_channel(api_key=api_key, channel_id=channel_id)
        if channel is not None:
            return update_sub_info(subscription, channel)
        return None

    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Item]:

        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != SubscriptionProvider.YOUTUBE:
            return []

        rss_items = await self.youtube_rss_client.get_youtube_items(
            playlist_id=subscription.external_data["playlist_id"])
        rss_items = [i for i in rss_items if i.published > from_date]
        if len(rss_items) == 0:
            return []

        if credential is not None:
            if credential.credential_type != ExternalServiceType.YOUTUBE_API_KEY:
                msg = "Invalid credential type"
                raise InvalidCredentialTypeError(msg)
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
            credential: ExternalServiceCredential | None = None,
    ) -> set[Item]:
        def link_to_video_id(link: str) -> str:
            return link.rsplit("/watch?v=", maxsplit=1)[-1]

        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids),
            page_number=0,
            limit=len(item_ids))

        items = [item for item in items if item.provider == ItemProvider.YOUTUBE]

        video_id_to_item: dict[str, Item] = {link_to_video_id(str(item.url)): item for item in items}

        updated_videos = await self.youtube_client.get_youtube_videos(
            api_key=self._get_api_key() if credential is None else credential.credential_value,
            video_ids=[link_to_video_id(str(item.url)) for item in items])

        return {v.to_item(item_id=video_id_to_item[v.video_id].uuid,
                                   sub_id=video_id_to_item[v.video_id].subscription_uuid)
                         for v in updated_videos}


    async def get_subscription_from_url(
            self,
            url: AnyUrl,
            credential: ExternalServiceCredential | None = None,
    ) -> Subscription | None:
        if url.host not in ["www.youtube.com", "youtube.com"]:
            return None

        try:
            youtube_channel: YoutubeChannel | None = None
            path = "" if url.path is None else url.path
            path_segments = path.split("/")
            if len(path_segments) == 2 and path_segments[1] != "":
                channel_name = path_segments[1]
                youtube_channel = await self.youtube_client.get_youtube_channel_from_name(
                    api_key=self._get_api_key() if credential is None else credential.credential_value,
                    channel_name=channel_name)
            elif len(path_segments) == 3 and path_segments[1] == "channel" and path_segments[2] != "":
                channel_id = path_segments[2]
                youtube_channel = await self.youtube_client.get_youtube_channel(
                    api_key=self._get_api_key() if credential is None else credential.credential_value,
                    channel_id=channel_id)

            if youtube_channel is not None:
                existing_sub = await self.subscription_repository.find_by_url(parse_url(youtube_channel.url))
                if existing_sub is not None:
                    return update_sub_info(existing_sub, youtube_channel)

                return Subscription.new(
                    uuid=uuid.uuid4(),
                    name=youtube_channel.title,
                    provider=SubscriptionProvider.YOUTUBE,
                    url=parse_url(youtube_channel.url),
                    thumbnail=utils.parse_url(youtube_channel.thumbnail_url),
                    external_data={
                        "channel_id": youtube_channel.channel_id,
                        "playlist_id": youtube_channel.playlist_id,
                    },
                )
        except YoutubeApiError as exception:
            logging.exception("Error while getting subscription from URL: %s", exception)

        return None

    async def get_subscriptions_from_name(
            self,
            name: str,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Subscription]:
        api_key = self._get_api_key() if credential is None else credential.credential_value

        channel = await self.youtube_client.get_youtube_channel_from_name(channel_name=name, api_key=api_key)
        if channel is not None:
            existing_sub = await self.subscription_repository.find_by_url(parse_url(channel.url))
            if existing_sub is not None:
                return [update_sub_info(existing_sub, channel)]

            return [Subscription.new(
                uuid=uuid.uuid4(),
                name=channel.title,
                provider=SubscriptionProvider.YOUTUBE,
                url=parse_url(channel.url),
                thumbnail=utils.parse_url(channel.thumbnail_url),
                external_data={
                    "channel_id": channel.channel_id,
                    "playlist_id": channel.playlist_id,
                },
            )]

        return []

    async def _get_api_key_for_sub(self, sub_id: uuid.UUID) -> str:
        subscribed_users = await self.user_repository.find_users_subscribed_to_subscription(sub_id)
        if len(subscribed_users) == 0:
            return self._get_api_key()

        credentials = await self.credentials_repository.find_by_users_and_type(
            user_ids=[u.uuid for u in subscribed_users],
            credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        )

        if len(credentials) == 0:
            return self._get_api_key()

        return credentials[randint(0, len(credentials) - 1)].credential_value

    def _get_api_key(self) -> str:
        return self.api_keys[randint(0, len(self.api_keys) - 1)]


def update_sub_info(sub: Subscription, youtube_channel: YoutubeChannel) -> Subscription:
    updated_sub = deepcopy(sub)
    updated_sub.name = youtube_channel.title
    updated_sub.url = parse_url(youtube_channel.url)
    updated_sub.thumbnail = parse_url(youtube_channel.thumbnail_url)
    updated_sub.external_data["channel_id"] = youtube_channel.channel_id
    updated_sub.external_data["playlist_id"] = youtube_channel.playlist_id
    updated_sub.updated_at = datetime_now()
    return updated_sub
