import math
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4

from pydantic import AnyUrl

from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.spotify.spotify_api_client import SpotifyApiClient, ShowImage, Show, \
    Episode, ReleaseDataPrecision

SHOW_ID_KEY = 'show_id'


class SpotifySubscriptionService(SubscriptionService):
    def __init__(self, spotify_client: SpotifyApiClient,
                 user_repository: UserRepository,
                 item_repository: ItemRepository,
                 subscription_repository: SubscriptionRepository):
        self.user_repository = user_repository
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository
        self.spotify_client = spotify_client

    async def get_subscriptions(
            self,
            user_id: UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Subscription]:
        return []

    async def get_subscription(
            self,
            sub_id: UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> Optional[Subscription]:
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None:
            return None

        if subscription.provider != SubscriptionProvider.SPOTIFY:
            return None

        show_id = subscription.external_data.get(SHOW_ID_KEY)
        if show_id is None:
            return None

        spotify_shows = await self.spotify_client.get_shows([show_id])
        if len(spotify_shows) == 0:
            return None

        return map_spotify_show_to_subscription(spotify_shows[0], sub_id)

    async def get_items(
            self,
            item_ids: set[UUID],
            credential: Optional[ExternalServiceCredential] = None
    ) -> set[Item]:
        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids, provider=ItemProvider.SPOTIFY),
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
                item_id=episode_index[episode.id].uuid
            )
            for episode in episodes
        }

    async def get_subscription_items(
            self,
            sub_id: UUID,
            from_date: datetime,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Item]:
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None:
            return []

        if subscription.provider != SubscriptionProvider.SPOTIFY:
            return []

        show_id = str(subscription.external_data.get(SHOW_ID_KEY))
        if show_id is None:
            return []

        items: list[Item] = []
        offset = 0
        while True:
            response = await self.spotify_client.get_show_episodes(show_id, offset)
            new_items = [map_episode_to_item(episode, sub_id) for episode in response.items]
            filtered_new_items = [item for item in new_items if item.published_at >= from_date]
            items += filtered_new_items

            if len(filtered_new_items) == 0 or len(new_items) != len(filtered_new_items):
                break

            offset += len(response.items)

        return [item for item in items if item.published_at >= from_date]

    async def get_subscription_from_url(
            self,
            url: AnyUrl,
            credential: Optional[ExternalServiceCredential] = None
    ) -> Subscription | None:
        if url.host != 'open.spotify.com':
            return None

        split_url = url.path.split('/') if url.path else []
        if len(split_url) < 3:
            return None

        show_id = split_url[-1]
        spotify_shows = await self.spotify_client.get_shows([show_id])
        if len(spotify_shows) == 0:
            return None

        sub_uuid = uuid4()
        if exiting_sub := await self.subscription_repository.find_by_url(url):
            sub_uuid = exiting_sub.uuid

        return map_spotify_show_to_subscription(spotify_shows[0], sub_uuid)

    async def get_subscriptions_from_name(
            self,
            name: str,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Subscription]:
        spotify_show = await self.spotify_client.find_show(name)
        if spotify_show is None:
            return []

        show_url = AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}")
        sub_uuid = uuid4()
        if exiting_sub := await self.subscription_repository.find_by_url(show_url):
            sub_uuid = exiting_sub.uuid

        sub = map_spotify_show_to_subscription(spotify_show, sub_uuid)
        return [sub]


def map_spotify_show_to_subscription(spotify_show: Show, sub_uuid: UUID | None = None) -> Subscription:
    sub_uuid = sub_uuid or uuid4()
    thumbnail = get_most_similar_image(spotify_show.images, 320, 200)
    if thumbnail is None:
        raise ValueError("No thumbnail found")

    show_url = AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}")

    return Subscription.new(
        uuid=sub_uuid,
        name=spotify_show.name,
        provider=SubscriptionProvider.SPOTIFY,
        url=show_url,
        thumbnail=thumbnail.url,
        external_data={
            SHOW_ID_KEY: spotify_show.id
        }
    )


def map_episode_to_item(episode: Episode, sub_id: UUID, item_id: UUID | None = None) -> Item:
    thumbnail = get_most_similar_image(episode.images, 320, 200)
    if thumbnail is None:
        raise ValueError("No thumbnail found")

    return Item.new(
        uuid=item_id or uuid4(),
        subscription_uuid=sub_id,
        name=episode.name,
        description=episode.description,
        url=AnyUrl(f"https://open.spotify.com/episode/{episode.id}"),
        thumbnail=thumbnail.url,
        provider=ItemProvider.SPOTIFY,
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
        return url.path.split('/')[-1]
    raise ValueError(f"Invalid spotify URL: {url}")


def calculate_duration(duration_ms: int) -> int:
    return math.ceil(duration_ms / 1000)


def calculate_date(date: str, precision: ReleaseDataPrecision) -> datetime:
    if precision == ReleaseDataPrecision.DAY:
        return datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if precision == ReleaseDataPrecision.MONTH:
        return datetime.strptime(date, "%Y-%m").replace(tzinfo=timezone.utc)
    if precision == ReleaseDataPrecision.YEAR:
        return datetime.strptime(date, "%Y").replace(tzinfo=timezone.utc)
    raise ValueError(f"Invalid precision: {precision}")
