import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from random import randint
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
import backoff
import isodate  # type: ignore

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import InvalidCredentialTypeError
from linkurator_core.domain.items.item import Item, YOUTUBE_ITEM_VERSION
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceType, ExternalServiceCredential
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.account_service import GoogleAccountService

MAX_VIDEOS_PER_QUERY = 50


@dataclass
class YoutubeChannel:
    title: str
    channel_id: str
    channel_title: str
    description: str
    published_at: str
    thumbnail_url: str
    url: str
    playlist_id: str
    country: str

    @staticmethod
    def from_dict(channel: dict):
        return YoutubeChannel(
            title=channel["snippet"]["title"],
            channel_id=channel["id"],
            channel_title=channel["snippet"]["title"],
            description=channel["snippet"]["description"],
            published_at=channel["snippet"]["publishedAt"],
            thumbnail_url=channel["snippet"]["thumbnails"]["medium"]["url"],
            url=f'https://www.youtube.com/channel/{channel["id"]}',
            playlist_id=channel["contentDetails"]["relatedPlaylists"]["uploads"],
            country=channel['snippet'].get('country', '')
        )

    def to_subscription(self, sub_id: uuid.UUID) -> Subscription:
        return Subscription.new(
            uuid=sub_id,
            name=self.title,
            provider=SubscriptionProvider.YOUTUBE,
            external_data={
                "channel_id": self.channel_id,
                "playlist_id": self.playlist_id
            },
            url=utils.parse_url(self.url),
            thumbnail=utils.parse_url(self.thumbnail_url)
        )


@dataclass
class YoutubeVideo:
    title: str
    description: str
    video_id: str
    published_at: datetime
    thumbnail_url: str
    url: str
    channel_id: str
    channel_url: str
    country: str
    duration: str

    @staticmethod
    def from_dict(video: dict):
        published_at = datetime.strptime(video["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")

        return YoutubeVideo(
            title=video["snippet"]["title"],
            description=video["snippet"]["description"],
            video_id=video["id"],
            published_at=published_at.replace(tzinfo=timezone.utc),
            thumbnail_url=video["snippet"]["thumbnails"]["medium"]["url"],
            url=f'https://www.youtube.com/watch?v={video["id"]}',
            channel_id=video["snippet"]["channelId"],
            channel_url=f'https://www.youtube.com/channel/{video["snippet"]["channelId"]}',
            country=video['snippet'].get('country', ''),
            duration=video['contentDetails']['duration']
        )

    def to_item(self, item_id: uuid.UUID, sub_id: uuid.UUID) -> Item:
        return Item.new(
            uuid=item_id,
            subscription_uuid=sub_id,
            name=self.title,
            description=self.description,
            url=utils.parse_url(self.url),
            thumbnail=utils.parse_url(self.thumbnail_url),
            published_at=self.published_at,
            duration=isodate.parse_duration(self.duration).total_seconds(),
            version=YOUTUBE_ITEM_VERSION
        )


class YoutubeApiClient:
    def __init__(self):
        self.base_url = "https://youtube.googleapis.com/youtube/v3"

    async def get_youtube_user_channel(self, access_token: str) -> Optional[YoutubeChannel]:
        response_json, status_code = await self._request_youtube_user_channel(access_token)
        if status_code != 200:
            return None

        items = response_json.get("items", [])
        if len(items) == 0:
            return None

        return YoutubeChannel.from_dict(items[0])

    async def get_youtube_subscriptions(self, access_token: str, api_key: str) -> List[YoutubeChannel]:
        next_page_token = None
        subscriptions: List[YoutubeChannel] = []

        while True:
            subs_response_json, subs_status_code = await self._request_youtube_subscriptions(
                access_token, next_page_token)
            if subs_status_code != 200:
                raise Exception(f"Error getting youtube subscriptions: {subs_response_json}")

            next_page_token = subs_response_json.get("nextPageToken", None)

            # Get channels associated to the subscriptions
            channel_ids = [d["snippet"]["resourceId"]["channelId"] for d in subs_response_json["items"]]

            channels_response_json, channels_status_code = await self._request_youtube_channels(
                api_key, channel_ids)
            if channels_status_code != 200:
                raise Exception(f"Error getting youtube channels: {channels_response_json}")

            youtube_channels = list(channels_response_json["items"])
            youtube_channels.sort(key=lambda i: i["id"])

            subscriptions = subscriptions + [YoutubeChannel.from_dict(c) for c in youtube_channels]

            # Stop if there are no more subscription to process
            if next_page_token is None:
                break

        return subscriptions

    async def get_youtube_channel(self, api_key: str, channel_id: str) -> Optional[YoutubeChannel]:
        channel_response_json, channel_status_code = await self._request_youtube_channels(
            api_key, [channel_id])

        if channel_status_code != 200:
            raise Exception(f"Error getting youtube channel: {channel_response_json}")

        return YoutubeChannel.from_dict(channel_response_json["items"][0])

    async def get_youtube_videos(self, api_key: str, video_ids: List[str]) -> List[YoutubeVideo]:
        youtube_videos: List[YoutubeVideo] = []

        for i in range(0, len(video_ids), MAX_VIDEOS_PER_QUERY):
            videos_response_json, videos_status_code = await self._request_youtube_videos(
                api_key, video_ids[i:i + MAX_VIDEOS_PER_QUERY])

            if videos_status_code != 200:
                raise Exception(f"Error getting youtube videos: {videos_response_json}")

            youtube_videos = youtube_videos + [YoutubeVideo.from_dict(v) for v in videos_response_json["items"]]

        return youtube_videos

    async def get_youtube_videos_from_playlist(
            self, api_key: str, playlist_id: str, from_date: datetime
    ) -> List[YoutubeVideo]:
        next_page_token = None
        videos: List[YoutubeVideo] = []

        logging.debug("Starting to retrieve videos from playlist %s", playlist_id)

        while True:
            playlist_response_json, playlist_status_code = await self._request_youtube_playlist_items(
                api_key, playlist_id, next_page_token)
            if playlist_status_code == 404:
                logging.debug("Playlist %s not found", playlist_id)
                break
            if playlist_status_code != 200:
                raise Exception(f"Error getting youtube playlist items: {playlist_response_json}")

            next_page_token = playlist_response_json.get("nextPageToken", None)

            # Get videos associated to the playlist
            playlist_items = playlist_response_json["items"]
            filtered_video_ids = [playlist_item["snippet"]["resourceId"]["videoId"]
                                  for playlist_item in playlist_items
                                  if playlist_item["snippet"]["publishedAt"] >= from_date.isoformat()]

            youtube_videos = []
            if len(filtered_video_ids) > 0:
                videos_response_json, videos_status_code = await self._request_youtube_videos(
                    api_key, filtered_video_ids)
                if videos_status_code != 200:
                    raise Exception(f"Error getting youtube videos: {videos_response_json}")

                youtube_videos = list(videos_response_json["items"])
                youtube_videos.sort(key=lambda i: i["id"])

            videos = videos + [YoutubeVideo.from_dict(v) for v in youtube_videos]

            logging.debug("Retrieved %s videos", len(videos))
            if len(videos) > 0:
                logging.debug("Last video published at %s", videos[-1].published_at)

            # Stop if there are no more videos to process
            if next_page_token is None or len(filtered_video_ids) < len(playlist_items):
                break

        videos.sort(key=lambda i: i.published_at, reverse=True)
        logging.debug("Retrieved %s videos from playlist %s", len(videos), playlist_id)
        return videos

    @backoff.on_exception(backoff.expo,
                          aiohttp.ClientConnectorError,
                          max_time=60,
                          jitter=None)
    async def _request_youtube_user_channel(self, access_token: str) -> Tuple[Dict[str, Any], int]:
        youtube_api_url = f"{self.base_url}/channels"

        channel_query_params: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "mine": True,
        }

        url = f"{youtube_api_url}?{urlencode(channel_query_params)}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"Authorization": f"Bearer {access_token}"}) as response:
                return await response.json(), response.status

    @backoff.on_exception(backoff.expo,
                          aiohttp.ClientConnectorError,
                          max_time=60,
                          jitter=None)
    async def _request_youtube_subscriptions(
            self, access_token: str, next_page_token: Optional[str]
    ) -> Tuple[Dict[str, Any], int]:
        youtube_api_url = f"{self.base_url}/subscriptions"

        subs_query_params: Dict[str, Any] = {
            "part": "snippet",
            "maxResults": 50,
            "mine": "true",
        }
        if next_page_token is not None:
            subs_query_params["pageToken"] = next_page_token

        url = f"{youtube_api_url}?{urlencode(subs_query_params)}"

        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {access_token}"}) as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status

    @backoff.on_exception(backoff.expo,
                          aiohttp.ClientConnectorError,
                          max_time=60,
                          jitter=None)
    async def _request_youtube_channels(self, api_key: str, channel_ids: List[str]) -> Tuple[Dict[str, Any], int]:
        youtube_api_channels_url = f"{self.base_url}/channels"

        channels_query_params: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "id": ",".join(channel_ids),
            "maxResults": 50,
            "key": api_key
        }

        url = f"{youtube_api_channels_url}?{urlencode(channels_query_params)}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status

    @backoff.on_exception(backoff.expo,
                          aiohttp.ClientConnectorError,
                          max_time=60,
                          jitter=None)
    async def _request_youtube_playlist_items(
            self, api_key: str, playlist_id: str, next_page_token: Optional[str]
    ) -> Tuple[Dict[str, Any], int]:
        youtube_api_url = f"{self.base_url}/playlistItems"

        playlist_items_query_params: Dict[str, Any] = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": MAX_VIDEOS_PER_QUERY,
            "key": api_key
        }
        if next_page_token is not None:
            playlist_items_query_params["pageToken"] = next_page_token

        url = f"{youtube_api_url}?{urlencode(playlist_items_query_params)}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status

    @backoff.on_exception(backoff.expo,
                          aiohttp.ClientConnectorError,
                          max_time=60,
                          jitter=None)
    async def _request_youtube_videos(
            self, api_key: str, video_ids: List[str]
    ) -> Tuple[Dict[str, Any], int]:
        youtube_api_videos_url = f"{self.base_url}/videos"

        videos_query_params: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "id": ",".join(video_ids),
            "maxResults": MAX_VIDEOS_PER_QUERY,
            "key": api_key
        }

        url = f"{youtube_api_videos_url}?{urlencode(videos_query_params)}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status


class YoutubeService(SubscriptionService):
    def __init__(self, google_account_service: GoogleAccountService,
                 user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository,
                 credentials_repository: ExternalCredentialRepository,
                 youtube_client: YoutubeApiClient,
                 api_key: str):
        self.google_account_service = google_account_service
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.credentials_repository = credentials_repository
        self.youtube_client = youtube_client
        self.api_key = api_key

    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Subscription]:
        user = self.user_repository.get(user_id)
        youtube_channels = []

        api_key = self.api_key
        if credential is not None:
            if not credential.credential_type == ExternalServiceType.YOUTUBE_API_KEY:
                raise InvalidCredentialTypeError("Invalid credential type")
            api_key = credential.credential_value

        if user is not None and user.google_refresh_token is not None:
            access_token = self.google_account_service.generate_access_token_from_refresh_token(
                user.google_refresh_token)

            if access_token is not None:
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

        items, _ = self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids),
            page_number=0,
            limit=len(item_ids))

        video_id_to_item: Dict[str, Item] = {link_to_video_id(str(item.url)): item for item in items}

        updated_videos = await self.youtube_client.get_youtube_videos(
            api_key=self.api_key if credential is None else credential.credential_value,
            video_ids=[link_to_video_id(str(item.url)) for item in items])

        updated_items = {v.to_item(item_id=video_id_to_item[v.video_id].uuid,
                                   sub_id=video_id_to_item[v.video_id].subscription_uuid)
                         for v in updated_videos}

        return updated_items

    async def _get_api_key_for_sub(self, sub_id: uuid.UUID) -> str:
        subscribed_users = self.user_repository.find_users_subscribed_to_subscription(sub_id)
        if len(subscribed_users) == 0:
            return self.api_key

        credentials = await self.credentials_repository.find_by_users_and_type(
            user_ids=[u.uuid for u in subscribed_users],
            credential_type=ExternalServiceType.YOUTUBE_API_KEY
        )

        if len(credentials) == 0:
            return self.api_key

        return credentials[randint(0, len(credentials) - 1)].credential_value
