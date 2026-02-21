from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime

from pydantic import AnyUrl

from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.item import DEFAULT_ITEM_VERSION, Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.infrastructure.patreon.patreon_api_client import PatreonApiClient, PatreonCampaign, PatreonPost

PATREON_PROVIDER_NAME = "patreon"
PATREON_PROVIDER_ALIAS = "Patreon"
PATREON_PROVIDER_VERSION = DEFAULT_ITEM_VERSION
PATREON_REFRESH_PERIOD_MINUTES = 60  # 1 hour

VANITY_KEY = "vanity"
CAMPAIGN_ID_KEY = "campaign_id"
DEFAULT_PATREON_ICON = "https://c5.patreon.com/external/favicon/rebrand/favicon.svg"


class PatreonSubscriptionService(SubscriptionService):
    """
    Patreon subscription service using Patreon API v2.

    Note: Fetching posts from a creator requires their OAuth access token.
    The credential parameter should contain a PATREON_CREATOR_ACCESS_TOKEN.
    """

    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        item_repository: ItemRepository,
        patreon_client: PatreonApiClient,
    ) -> None:
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.patreon_client = patreon_client

    def provider_name(self) -> ItemProvider:
        return PATREON_PROVIDER_NAME

    def provider_alias(self) -> str:
        return PATREON_PROVIDER_ALIAS

    def provider_version(self) -> int:
        return PATREON_PROVIDER_VERSION

    def refresh_period_minutes(self) -> int:
        return PATREON_REFRESH_PERIOD_MINUTES

    def provider_thumbnail(self) -> str:
        return DEFAULT_PATREON_ICON

    async def get_subscriptions(
        self,
        user_id: uuid.UUID,  # noqa: ARG002
        access_token: str,
    ) -> list[Subscription]:
        """
        Get Patreon subscriptions (memberships) for the authenticated user.
        """
        membershipts = await self.patreon_client.get_current_user_memberships(access_token)

        campaigns: list[PatreonCampaign] = []
        for membership in membershipts:
            campaign = await self.patreon_client.get_campaign(membership.campaign_id)
            if campaign is not None:
                campaigns.append(campaign)

        return [map_patreon_campaign_to_subscription(campaign) for campaign in campaigns]

    async def get_subscription(
        self,
        sub_id: uuid.UUID,
    ) -> Subscription | None:
        """Get and update subscription information from Patreon API."""
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != self.provider_name():
            return None

        campaign_id = subscription.external_data.get(CAMPAIGN_ID_KEY)
        if campaign_id is None:
            return None

        campaign = await self.patreon_client.get_campaign(campaign_id)
        if campaign is None:
            return None

        return map_patreon_campaign_to_subscription(campaign, subscription)

    async def get_subscription_items(
        self,
        sub_id: uuid.UUID,
        from_date: datetime,
    ) -> list[Item]:
        """
        Get posts from Patreon campaign published after from_date.
        """
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != self.provider_name():
            return []

        campaign_id = subscription.external_data.get(CAMPAIGN_ID_KEY)
        if not campaign_id:
            return []

        posts = await self.patreon_client.get_campaign_posts(campaign_id, from_date)
        return [map_patreon_post_to_item(post, sub_id) for post in posts]

    async def get_items(
        self,
        item_ids: set[uuid.UUID],
    ) -> set[Item]:
        """
        Get specific items by ID from Patreon.

        Fetches individual posts from the API.
        """
        # Fetch items from repository to get their post IDs
        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids, provider=self.provider_name()),
            page_number=0,
            limit=len(item_ids),
        )

        updated_items: set[Item] = set()

        for item in items:
            # Extract post ID from URL (e.g., patreon.com/posts/12345)
            post_id = extract_post_id_from_url(item.url)
            if not post_id:
                continue

            post = await self.patreon_client.get_post(post_id)
            if post:
                updated_item = map_patreon_post_to_item(post, item.subscription_uuid)
                updated_item.uuid = item.uuid
                updated_item.created_at = item.created_at
                updated_items.add(updated_item)

        return updated_items

    async def get_subscription_from_url(
        self,
        url: AnyUrl,
    ) -> Subscription | None:
        """
        Get or create subscription from Patreon URL.

        Note: Without an access token, we can only create a basic subscription
        that will need to be updated later with campaign details.
        """
        vanity = extract_vanity_from_url(url)
        if vanity is None:
            return None

        campaign_id = await self.patreon_client.get_campaign_id_from_vanity(vanity)
        if campaign_id is None:
            return None

        # Check if subscription already exists by URL pattern
        existing_sub = await self.subscription_repository.find_by_url(url)

        campaign = await self.patreon_client.get_campaign(campaign_id)

        if campaign:
            return map_patreon_campaign_to_subscription(campaign, existing_sub)

        # If no API access or campaign not found, create a placeholder subscription
        if existing_sub:
            return existing_sub

        return None

    async def get_subscriptions_from_name(
        self,
        name: str,  # noqa: ARG002
    ) -> list[Subscription]:
        """
        Search for Patreon creators by name.

        Patreon API v2 doesn't provide a public search endpoint,
        so this method returns an empty list.
        """
        return []


def map_patreon_post_to_item(post: PatreonPost, subscription_id: uuid.UUID) -> Item:
    """Map Patreon post to domain Item."""
    thumbnail = parse_url(post.image_url) if post.image_url else parse_url(DEFAULT_PATREON_ICON)
    return Item.new(
        uuid=uuid.uuid4(),
        subscription_uuid=subscription_id,
        name=post.title,
        description="",
        url=parse_url(post.url),
        thumbnail=thumbnail,
        published_at=post.published_at,
        provider=PATREON_PROVIDER_NAME,
        version=PATREON_PROVIDER_VERSION,
        duration=post.duration_seconds,
    )


def map_patreon_campaign_to_subscription(
        campaign: PatreonCampaign,
        existing_sub: Subscription | None = None,
) -> Subscription:
    """Map Patreon campaign to domain Subscription."""
    avatar_thumbnail: AnyUrl | None = None
    if campaign.avatar_photo_image_urls is not None and campaign.avatar_photo_image_urls.default is not None:
        avatar_thumbnail = campaign.avatar_photo_image_urls.default
    thumbnail = avatar_thumbnail if avatar_thumbnail is not None else parse_url(DEFAULT_PATREON_ICON)

    if existing_sub is not None:
        updated_sub = deepcopy(existing_sub)
        updated_sub.name = campaign.vanity
        updated_sub.thumbnail = thumbnail
        updated_sub.description = campaign.creation_name + " - " + (campaign.summary or "")
        updated_sub.external_data[VANITY_KEY] = campaign.vanity
        updated_sub.external_data[CAMPAIGN_ID_KEY] = campaign.id
        return updated_sub

    external_data: dict[str, str] = {
        VANITY_KEY: campaign.vanity,
        CAMPAIGN_ID_KEY: campaign.id,
    }

    return Subscription.new(
        uuid=uuid.uuid4(),
        name=campaign.vanity,
        provider=PATREON_PROVIDER_NAME,
        url=parse_url(campaign.url),
        thumbnail=thumbnail,
        description=campaign.summary or "",
        external_data=external_data,
    )


def extract_vanity_from_url(url: AnyUrl) -> str | None:
    """
    Extract campaign ID or vanity from Patreon URL.

    Supported formats:
    - patreon.com/username
    - patreon.com/c/username
    - patreon.com/m/campaign_id
    """
    if url.host not in ["www.patreon.com", "patreon.com"]:
        return None

    path = url.path or ""
    path_segments = [s for s in path.split("/") if s]

    if len(path_segments) == 0:
        return None

    # Handle URLs like:
    # - patreon.com/username -> returns vanity (username)
    # - patreon.com/c/username -> returns vanity (username)
    # - patreon.com/cw/username -> returns vanity (username)
    if len(path_segments) == 1:
        return path_segments[0]
    if len(path_segments) >= 2 and path_segments[0] in ("c", "cw"):
        return path_segments[1]

    return None


def extract_post_id_from_url(url: AnyUrl) -> str | None:
    """Extract post ID from Patreon post URL."""
    if url.host not in ["www.patreon.com", "patreon.com"]:
        return None

    path = url.path or ""
    # URLs like patreon.com/posts/title-12345 or patreon.com/posts/12345
    if "/posts/" in path:
        # The post ID is the last segment after the last dash, or just the last segment
        last_segment = path.split("/")[-1]
        # If the segment contains a dash, the ID is after the last dash
        if "-" in last_segment:
            return last_segment.split("-")[-1]
        return last_segment

    return None
