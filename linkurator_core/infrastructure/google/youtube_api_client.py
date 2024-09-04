from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
import backoff
import isodate  # type: ignore

from linkurator_core.domain.common import utils
from linkurator_core.domain.items.item import Item, YOUTUBE_ITEM_VERSION
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider

MAX_VIDEOS_PER_QUERY = 50


class YoutubeApiError(Exception):
    pass


class LiveBroadcastContent(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    NONE = "none"


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
    def from_dict(channel: dict[str, Any]) -> YoutubeChannel:
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
    live_broadcast_content: LiveBroadcastContent

    @staticmethod
    def from_dict(video: dict[str, Any]) -> YoutubeVideo:
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
            duration=video['contentDetails']['duration'],
            live_broadcast_content=LiveBroadcastContent(video["snippet"]["liveBroadcastContent"])
        )

    def to_item(self, item_id: uuid.UUID, sub_id: uuid.UUID,
                current_date: datetime = datetime.now(tz=timezone.utc)) -> Item:
        deleted_at: Optional[datetime] = None
        if self.live_broadcast_content == LiveBroadcastContent.UPCOMING and \
                self.published_at + timedelta(days=365) < current_date:
            deleted_at = current_date
        return Item.new(
            uuid=item_id,
            subscription_uuid=sub_id,
            name=self.title,
            description=self.description,
            url=utils.parse_url(self.url),
            thumbnail=utils.parse_url(self.thumbnail_url),
            published_at=self.published_at,
            duration=isodate.parse_duration(self.duration).total_seconds(),
            version=YOUTUBE_ITEM_VERSION,
            deleted_at=deleted_at
        )


class YoutubeApiClient:
    def __init__(self) -> None:
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
                raise YoutubeApiError(f"Error getting youtube subscriptions: {subs_response_json}")

            next_page_token = subs_response_json.get("nextPageToken", None)

            # Get channels associated to the subscriptions
            channel_ids = [d["snippet"]["resourceId"]["channelId"] for d in subs_response_json["items"]]

            channels_response_json, channels_status_code = await self._request_youtube_channels(
                api_key, channel_ids)
            if channels_status_code != 200:
                raise YoutubeApiError(f"Error getting youtube channels: {channels_response_json}")

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
            raise YoutubeApiError(f"Error getting youtube channel: {channel_response_json}")

        return YoutubeChannel.from_dict(channel_response_json["items"][0])

    async def get_youtube_videos(self, api_key: str, video_ids: List[str]) -> List[YoutubeVideo]:
        youtube_videos: List[YoutubeVideo] = []

        for i in range(0, len(video_ids), MAX_VIDEOS_PER_QUERY):
            videos_response_json, videos_status_code = await self._request_youtube_videos(
                api_key, video_ids[i:i + MAX_VIDEOS_PER_QUERY])

            if videos_status_code != 200:
                raise YoutubeApiError(f"Error getting youtube videos: {videos_response_json}")

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
                raise YoutubeApiError(f"Error getting youtube playlist items: {playlist_response_json}")

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
                    raise YoutubeApiError(f"Error getting youtube videos: {videos_response_json}")

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
