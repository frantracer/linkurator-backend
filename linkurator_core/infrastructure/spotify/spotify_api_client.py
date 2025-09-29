from __future__ import annotations

import logging
from base64 import b64encode
from enum import Enum
from typing import Any

import aiohttp
from pydantic import AnyUrl, BaseModel
from unidecode import unidecode


class ReleaseDataPrecision(str, Enum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class ShowImage(BaseModel):
    url: AnyUrl
    height: int
    width: int


class Show(BaseModel):
    id: str
    images: list[ShowImage]
    name: str
    total_episodes: int
    description: str


class Episode(BaseModel):
    description: str
    duration_ms: int
    id: str
    images: list[ShowImage]
    name: str
    release_date: str
    release_date_precision: ReleaseDataPrecision


class GetEpisodesResponse(BaseModel):
    items: list[Episode]
    total: int


class SpotifyApiHttpError(Exception):
    pass


class SpotifyApiClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_access_token(self) -> str | None:
        auth_url = "https://accounts.spotify.com/api/token"

        # Encode client_id and client_secret in base64
        auth_header = b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_header}",
        }
        data = {
            "grant_type": "client_credentials",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, headers=headers, data=data) as response:
                if response.status == 200:
                    body = await response.json()
                    return body["access_token"]
                logging.error("Failed to retrieve token: %s -> %s", response.status, await response.text())
                return None

    async def find_show(self, query: str) -> Show | None:
        token = await self.get_access_token()
        if token is None:
            return None

        search_url = "https://api.spotify.com/v1/search"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        params = {
            "q": query,
            "type": "show",
            "limit": "5",
            "offset": "0",
            "market": "ES",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    shows = body.get("shows", {}).get("items", [])

                    for show in shows:
                        if unidecode(query.lower()) in unidecode(show["name"].lower()):
                            return map_json_to_show(show)

                    return None

                logging.error("Failed to retrieve show: %s -> %s", response.status, await response.text())
                return None

    async def get_shows(self, show_ids: list[str]) -> list[Show]:
        if len(show_ids) == 0:
            return []

        if len(show_ids) > 50:
            msg = "Cannot retrieve more than 50 shows at once"
            raise SpotifyApiHttpError(msg)

        token = await self.get_access_token()
        if token is None:
            msg = "Failed to retrieve token"
            raise SpotifyApiHttpError(msg)

        shows_url = "https://api.spotify.com/v1/shows"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        params = {
            "ids": ",".join(show_ids),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(shows_url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    shows_json = body.get("shows", [])
                    return [map_json_to_show(show_json) for show_json in shows_json]

                msg = f"Failed to retrieve shows: {response.status} -> {await response.text()}"
                raise SpotifyApiHttpError(msg)

    async def get_show_episodes(self, show_id: str, offset: int = 0, limit: int = 50) -> GetEpisodesResponse:
        if limit > 50:
            msg = "Cannot retrieve more than 50 episodes at once"
            raise SpotifyApiHttpError(msg)

        token = await self.get_access_token()
        if token is None:
            msg = "Failed to retrieve token"
            raise SpotifyApiHttpError(msg)

        episodes_url = f"https://api.spotify.com/v1/shows/{show_id}/episodes"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        params = {
            "limit": limit,
            "offset": offset,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(episodes_url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    episodes_json = body.get("items", [])
                    total_items = body.get("total", 0)
                    episodes = [map_json_to_episode(episode_json)
                                for episode_json in episodes_json
                                if episode_json is not None]
                    return GetEpisodesResponse(items=episodes, total=total_items)

                msg = f"Failed to retrieve episodes: {response.status} -> {await response.text()}"
                raise SpotifyApiHttpError(msg)

    async def get_episodes(self, episode_ids: list[str]) -> list[Episode]:
        if len(episode_ids) == 0:
            return []

        if len(episode_ids) > 50:
            msg = "Cannot retrieve more than 50 episodes at once"
            raise SpotifyApiHttpError(msg)

        token = await self.get_access_token()
        if token is None:
            msg = "Failed to retrieve token"
            raise SpotifyApiHttpError(msg)

        episodes_url = "https://api.spotify.com/v1/episodes"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        params = {
            "ids": ",".join(episode_ids),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(episodes_url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    episodes_json = body.get("episodes", [])
                    return [map_json_to_episode(episode_json) for episode_json in episodes_json]

                msg = f"Failed to retrieve episodes: {response.status} -> {await response.text()}"
                raise SpotifyApiHttpError(msg)


def map_json_to_show(json: dict[str, Any]) -> Show:
    return Show(
        id=json["id"],
        images=[
            ShowImage(
                url=image["url"],
                height=image["height"],
                width=image["width"],
            ) for image in json["images"]
        ],
        name=json["name"],
        total_episodes=json["total_episodes"],
        description=json["description"],
    )


def map_json_to_episode(json: dict[str, Any]) -> Episode:
    return Episode(
        id=json["id"],
        name=json["name"],
        description=json["description"],
        release_date=json["release_date"],
        release_date_precision=ReleaseDataPrecision(json["release_date_precision"]),
        duration_ms=json["duration_ms"],
        images=[
            ShowImage(
                url=image["url"],
                height=image["height"],
                width=image["width"],
            ) for image in json["images"]
        ],
    )
