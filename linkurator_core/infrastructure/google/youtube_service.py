from __future__ import annotations

import logging
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from random import randint

import isodate  # type: ignore
from pydantic import AnyUrl

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.utils import datetime_now, parse_url
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.youtube_api_client import (
    LiveBroadcastContent,
    YoutubeApiClient,
    YoutubeApiError,
    YoutubeChannel,
    YoutubeVideo,
)
from linkurator_core.infrastructure.google.youtube_rss_client import YoutubeRssClient

YOUTUBE_PROVIDER_NAME = "youtube"
YOUTUBE_PROVIDER_ALIAS = "YouTube"
YOUTUBE_PROVIDER_VERSION = 1
YOUTUBE_REFRESH_PERIOD_MINUTES = 5


class YoutubeService(SubscriptionService):
    def __init__(self,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository,
                 youtube_client: YoutubeApiClient,
                 youtube_rss_client: YoutubeRssClient,
                 api_keys: list[str]) -> None:
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.youtube_client = youtube_client
        self.youtube_rss_client = youtube_rss_client
        self.api_keys = api_keys

        if len(api_keys) == 0:
            msg = "No API keys provided"
            raise ValueError(msg)

    def provider_name(self) -> ItemProvider:
        return YOUTUBE_PROVIDER_NAME

    def provider_alias(self) -> str:
        return YOUTUBE_PROVIDER_ALIAS

    def provider_thumbnail(self) -> str:
        return "https://www.youtube.com/favicon.ico"

    def provider_version(self) -> int:
        return YOUTUBE_PROVIDER_VERSION

    def refresh_period_minutes(self) -> int:
        return YOUTUBE_REFRESH_PERIOD_MINUTES

    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            access_token: str,
    ) -> list[Subscription]:
        """
        Get subscriptions for a user from YouTube.

        :param user_id: user id
        :param access_token: access token for the user
        :return: list of subscriptions
        """
        user = await self.user_repository.get(user_id)
        youtube_channels = []

        if user is not None:
            channels = await self.youtube_client.get_youtube_subscriptions(access_token=access_token,
                                                                           api_key=self._get_api_key())
            youtube_channels = [map_youtube_channel_to_subscription(youtube_channel=c, sub_id=uuid.uuid4()) for c in channels]

        return youtube_channels

    async def get_subscription(
            self,
            sub_id: uuid.UUID,
    ) -> Subscription | None:
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != self.provider_name():
            return None

        channel_id = subscription.external_data["channel_id"]
        channel = await self.youtube_client.get_youtube_channel(api_key=self._get_api_key(), channel_id=channel_id)
        if channel is not None:
            return update_sub_info(subscription, channel)
        return None

    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
    ) -> list[Item]:

        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != self.provider_name():
            return []

        rss_items = await self.youtube_rss_client.get_youtube_items(
            playlist_id=subscription.external_data["playlist_id"])
        rss_items = [i for i in rss_items if i.published > from_date]
        if len(rss_items) == 0:
            return []

        videos = await self.youtube_client.get_youtube_videos_from_playlist(
            api_key=self._get_api_key(),
            playlist_id=subscription.external_data["playlist_id"],
            from_date=from_date)

        return [map_youtube_video_to_item(youtube_video=v, item_id=uuid.uuid4(), sub_id=sub_id)
                for v in videos]

    async def get_items(
            self,
            item_ids: set[uuid.UUID],
    ) -> set[Item]:
        def link_to_video_id(link: str) -> str:
            return link.rsplit("/watch?v=", maxsplit=1)[-1]

        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids),
            page_number=0,
            limit=len(item_ids))

        items = [item for item in items if item.provider == self.provider_name()]

        video_id_to_item: dict[str, Item] = {link_to_video_id(str(item.url)): item for item in items}

        updated_videos = await self.youtube_client.get_youtube_videos(
            api_key=self._get_api_key(),
            video_ids=[link_to_video_id(str(item.url)) for item in items])

        return {map_youtube_video_to_item(
            youtube_video=v,
            item_id=video_id_to_item[v.video_id].uuid,
            sub_id=video_id_to_item[v.video_id].subscription_uuid)
            for v in updated_videos}

    async def get_subscription_from_url(
            self,
            url: AnyUrl,
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
                    api_key=self._get_api_key(),
                    channel_name=channel_name)
            elif len(path_segments) == 3 and path_segments[1] == "channel" and path_segments[2] != "":
                channel_id = path_segments[2]
                youtube_channel = await self.youtube_client.get_youtube_channel(
                    api_key=self._get_api_key(),
                    channel_id=channel_id)

            if youtube_channel is not None:
                existing_sub = await self.subscription_repository.find_by_url(parse_url(youtube_channel.url))
                if existing_sub is not None:
                    return update_sub_info(existing_sub, youtube_channel)

                return Subscription.new(
                    uuid=uuid.uuid4(),
                    name=youtube_channel.title,
                    provider=self.provider_name(),
                    url=parse_url(youtube_channel.url),
                    thumbnail=utils.parse_url(youtube_channel.thumbnail_url),
                    external_data={
                        "channel_id": youtube_channel.channel_id,
                        "playlist_id": youtube_channel.playlist_id,
                    },
                    description=youtube_channel.description,
                )
        except YoutubeApiError as exception:
            logging.exception("Error while getting subscription from URL: %s", exception)

        return None

    async def get_subscriptions_from_name(
            self,
            name: str,
    ) -> list[Subscription]:
        channel = await self.youtube_client.get_youtube_channel_from_name(channel_name=name, api_key=self._get_api_key())
        if channel is not None:
            existing_sub = await self.subscription_repository.find_by_url(parse_url(channel.url))
            if existing_sub is not None:
                return [update_sub_info(existing_sub, channel)]

            return [Subscription.new(
                uuid=uuid.uuid4(),
                name=channel.title,
                provider=self.provider_name(),
                url=parse_url(channel.url),
                thumbnail=utils.parse_url(channel.thumbnail_url),
                external_data={
                    "channel_id": channel.channel_id,
                    "playlist_id": channel.playlist_id,
                },
                description=channel.description,
            )]

        return []

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
    updated_sub.description = youtube_channel.description
    return updated_sub


def map_youtube_channel_to_subscription(
        youtube_channel: YoutubeChannel,
        sub_id: uuid.UUID,
) -> Subscription:
    return Subscription.new(
        uuid=sub_id,
        name=youtube_channel.title,
        provider=YOUTUBE_PROVIDER_NAME,
        external_data={
            "channel_id": youtube_channel.channel_id,
            "playlist_id": youtube_channel.playlist_id,
        },
        url=utils.parse_url(youtube_channel.url),
        thumbnail=utils.parse_url(youtube_channel.thumbnail_url),
        description=youtube_channel.description,
    )


def map_youtube_video_to_item(
    youtube_video: YoutubeVideo,
    item_id: uuid.UUID,
    sub_id: uuid.UUID,
    current_date: datetime = datetime.now(tz=timezone.utc),
) -> Item:
    deleted_at: datetime | None = None
    if youtube_video.live_broadcast_content == LiveBroadcastContent.UPCOMING and \
            youtube_video.published_at + timedelta(days=365) < current_date:
        deleted_at = current_date
    return Item.new(
        uuid=item_id,
        subscription_uuid=sub_id,
        name=youtube_video.title,
        description=youtube_video.description,
        provider=YOUTUBE_PROVIDER_NAME,
        url=utils.parse_url(youtube_video.url),
        thumbnail=utils.parse_url(youtube_video.thumbnail_url),
        published_at=youtube_video.published_at,
        duration=isodate.parse_duration(youtube_video.duration).total_seconds(),
        version=YOUTUBE_PROVIDER_VERSION,
        deleted_at=deleted_at,
    )
