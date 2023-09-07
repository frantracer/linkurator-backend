import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
import backoff

from linkurator_core.domain.common import utils
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


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

    @staticmethod
    def from_dict(video: dict):
        return YoutubeVideo(
            title=video["snippet"]["title"],
            description=video["snippet"]["description"],
            video_id=video["id"],
            published_at=datetime.strptime(video["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"),
            thumbnail_url=video["snippet"]["thumbnails"]["medium"]["url"],
            url=f'https://www.youtube.com/watch?v={video["id"]}',
            channel_id=video["snippet"]["channelId"],
            channel_url=f'https://www.youtube.com/channel/{video["snippet"]["channelId"]}',
            country=video['snippet'].get('country', '')
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

    async def get_youtube_videos(self, api_key: str, playlist_id: str, from_date: datetime) -> List[YoutubeVideo]:
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
            "maxResults": 50,
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
            "maxResults": 50,
            "key": api_key
        }

        url = f"{youtube_api_videos_url}?{urlencode(videos_query_params)}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status


class YoutubeService(SubscriptionService):
    def __init__(self, google_account_service: GoogleAccountService, user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository, youtube_client: YoutubeApiClient,
                 api_key: str):
        self.google_account_service = google_account_service
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.youtube_client = youtube_client
        self.api_key = api_key

    async def get_subscriptions(self, user_id: uuid.UUID) -> List[Subscription]:
        user = self.user_repository.get(user_id)
        youtube_channels = []

        def map_channel_to_subscription(channel: YoutubeChannel) -> Subscription:
            return Subscription.new(
                uuid=uuid.uuid4(),
                name=channel.title,
                provider=SubscriptionProvider.YOUTUBE,
                external_data={
                    "channel_id": channel.channel_id,
                    "playlist_id": channel.playlist_id
                },
                url=utils.parse_url(channel.url),
                thumbnail=utils.parse_url(channel.thumbnail_url)
            )

        if user is not None and user.google_refresh_token is not None:
            access_token = self.google_account_service.generate_access_token_from_refresh_token(
                user.google_refresh_token)

            if access_token is not None:
                channels = await self.youtube_client.get_youtube_subscriptions(access_token=access_token,
                                                                               api_key=self.api_key)
                youtube_channels = [map_channel_to_subscription(c) for c in channels]

        return youtube_channels

    async def get_subscription(self, sub_id: uuid.UUID) -> Optional[Subscription]:
        subscription = self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != SubscriptionProvider.YOUTUBE:
            return None

        channel_id = subscription.external_data["channel_id"]

        channel = await self.youtube_client.get_youtube_channel(api_key=self.api_key, channel_id=channel_id)
        if channel is not None:
            subscription.name = channel.title
            subscription.url = utils.parse_url(channel.url)
            subscription.thumbnail = utils.parse_url(channel.thumbnail_url)
            return subscription
        return None

    async def get_items(self, sub_id: uuid.UUID, from_date: datetime) -> List[Item]:
        subscription = self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != SubscriptionProvider.YOUTUBE:
            return []

        def map_video_to_item(video: YoutubeVideo) -> Item:
            return Item.new(
                uuid=uuid.uuid4(),
                subscription_uuid=sub_id,
                name=video.title,
                description=video.description,
                url=utils.parse_url(video.url),
                thumbnail=utils.parse_url(video.thumbnail_url),
                published_at=video.published_at
            )

        videos = await self.youtube_client.get_youtube_videos(
            api_key=self.api_key,
            playlist_id=subscription.external_data["playlist_id"],
            from_date=from_date)

        return [map_video_to_item(v) for v in videos]
