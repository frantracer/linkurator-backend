from __future__ import annotations

import math
from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import AnyUrl

from linkurator_core.domain.items.item import DEFAULT_ITEM_VERSION, Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.spotify.spotify_api_client import (
    Episode,
    ReleaseDataPrecision,
    Show,
    ShowImage,
    SpotifyApiClient,
)

SHOW_ID_KEY = "show_id"
SPOTIFY_PROVIDER_NAME = "spotify"
SPOTIFY_PROVIDER_ALIAS = "Spotify"
SPOTIFY_PROVIDER_VERSION = DEFAULT_ITEM_VERSION
SPOTIFY_REFRESH_PERIOD_MINUTES = 60 * 6  # 6 hours


class SpotifySubscriptionService(SubscriptionService):
    def __init__(self, spotify_client: SpotifyApiClient,
                 user_repository: UserRepository,
                 item_repository: ItemRepository,
                 subscription_repository: SubscriptionRepository) -> None:
        self.user_repository = user_repository
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository
        self.spotify_client = spotify_client

    def provider_name(self) -> ItemProvider:
        return SPOTIFY_PROVIDER_NAME

    def provider_alias(self) -> str:
        return SPOTIFY_PROVIDER_ALIAS

    def provider_thumbnail(self) -> str:
        return "https://duckduckgo.com/assets/icons/favicons/spotify.2x.png"

    def provider_version(self) -> int:
        return SPOTIFY_PROVIDER_VERSION

    def refresh_period_minutes(self) -> int:
        return SPOTIFY_REFRESH_PERIOD_MINUTES

    async def get_subscriptions(
            self,
            user_id: UUID,  # noqa: ARG002
            access_token: str,  # noqa: ARG002
            credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> list[Subscription]:
        return []

    async def get_subscription(
            self,
            sub_id: UUID,
            credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> Subscription | None:
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None:
            return None

        if subscription.provider != self.provider_name():
            return None

        show_id = subscription.external_data.get(SHOW_ID_KEY)
        if show_id is None:
            return None

        spotify_shows = await self.spotify_client.get_shows([show_id])
        if len(spotify_shows) == 0:
            return None

        return map_spotify_show_to_subscription(spotify_shows[0], subscription)

    async def get_items(
            self,
            item_ids: set[UUID],
            credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> set[Item]:
        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids, provider=self.provider_name()),
            page_number=0,
            limit=len(item_ids))

        episode_index: dict[str, Item] = {
            episode_id_from_url(item.url): item
            for item in items
        }

        episodes_ids = list(episode_index.keys())
        episodes = []
        for i in range(0, len(episodes_ids), 50):
            episodes += await self.spotify_client.get_episodes(episodes_ids[i:i + 50])

        return {
            map_episode_to_item(
                episode=episode,
                sub_id=episode_index[episode.id].subscription_uuid,
                item_id=episode_index[episode.id].uuid,
            )
            for episode in episodes
        }

    async def get_subscription_items(
            self,
            sub_id: UUID,
            from_date: datetime,
            credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> list[Item]:
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None:
            return []

        if subscription.provider != self.provider_name():
            return []

        show_id = str(subscription.external_data.get(SHOW_ID_KEY))
        if show_id is None:
            return []

        items: list[Item] = []
        limit = 50
        offset = 0
        while True:
            response = await self.spotify_client.get_show_episodes(show_id, offset, limit)
            new_items = [map_episode_to_item(episode, sub_id) for episode in response.items]
            filtered_new_items = [item for item in new_items if item.published_at >= from_date]
            items += filtered_new_items

            if len(filtered_new_items) == 0 or len(new_items) != len(filtered_new_items):
                break

            offset += limit

        return [item for item in items if item.published_at >= from_date]

    async def get_subscription_from_url(
            self,
            url: AnyUrl,
            credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> Subscription | None:
        if url.host != "open.spotify.com":
            return None

        split_url = url.path.split("/") if url.path else []
        if len(split_url) < 3:
            return None

        show_id = split_url[-1]
        spotify_shows = await self.spotify_client.get_shows([show_id])
        if len(spotify_shows) == 0:
            return None

        existing_sub = await self.subscription_repository.find_by_url(url)

        return map_spotify_show_to_subscription(spotify_shows[0], existing_sub)

    async def get_subscriptions_from_name(
            self,
            name: str,
            credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> list[Subscription]:
        spotify_show = await self.spotify_client.find_show(name)
        if spotify_show is None:
            return []

        show_url = AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}")
        exiting_sub = await self.subscription_repository.find_by_url(show_url)

        sub = map_spotify_show_to_subscription(spotify_show, exiting_sub)
        return [sub]


def map_spotify_show_to_subscription(spotify_show: Show, sub: Subscription | None = None) -> Subscription:
    thumbnail = get_most_similar_image(spotify_show.images, 320, 200)
    if thumbnail is None:
        msg = "No thumbnail found"
        raise ValueError(msg)

    if sub is None:
        return Subscription.new(
            uuid=uuid4(),
            name=spotify_show.name,
            provider=SPOTIFY_PROVIDER_NAME,
            url=AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}"),
            thumbnail=thumbnail.url,
            external_data={
                SHOW_ID_KEY: spotify_show.id,
            },
            description=spotify_show.description,
        )

    updated_sub = deepcopy(sub)
    updated_sub.name = spotify_show.name
    updated_sub.thumbnail = thumbnail.url
    updated_sub.description = spotify_show.description
    return updated_sub


def map_episode_to_item(episode: Episode, sub_id: UUID, item_id: UUID | None = None) -> Item:
    thumbnail = get_most_similar_image(episode.images, 320, 200)
    if thumbnail is None:
        msg = "No thumbnail found"
        raise ValueError(msg)

    return Item.new(
        uuid=item_id or uuid4(),
        subscription_uuid=sub_id,
        name=episode.name,
        description=episode.description,
        url=AnyUrl(f"https://open.spotify.com/episode/{episode.id}"),
        thumbnail=thumbnail.url,
        provider=SPOTIFY_PROVIDER_NAME,
        version=SPOTIFY_PROVIDER_VERSION,
        published_at=calculate_date(episode.release_date, episode.release_date_precision),
        duration=calculate_duration(episode.duration_ms),
    )


def get_most_similar_image(images: list[ShowImage], width: int, height: int) -> ShowImage | None:
    if len(images) == 0:
        return None

    def image_diff(image: ShowImage) -> int:
        return abs(image.width - width) + abs(image.height - height)

    return min(images, key=image_diff)


def episode_id_from_url(url: AnyUrl) -> str:
    if url.path:
        return url.path.split("/")[-1]
    msg = f"Invalid spotify URL: {url}"
    raise ValueError(msg)


def calculate_duration(duration_ms: int) -> int:
    return math.ceil(duration_ms / 1000)


def calculate_date(date: str, precision: ReleaseDataPrecision) -> datetime:
    if precision == ReleaseDataPrecision.DAY:
        return datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if precision == ReleaseDataPrecision.MONTH:
        return datetime.strptime(date, "%Y-%m").replace(tzinfo=timezone.utc)
    if precision == ReleaseDataPrecision.YEAR:
        return datetime.strptime(date, "%Y").replace(tzinfo=timezone.utc)
    msg = f"Invalid precision: {precision}"
    raise ValueError(msg)
