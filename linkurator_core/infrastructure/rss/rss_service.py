from __future__ import annotations

import logging
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime

from pydantic import AnyUrl

from linkurator_core.domain.common.exceptions import InvalidRssFeedError
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.item import DEFAULT_ITEM_VERSION, Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential
from linkurator_core.infrastructure.rss.rss_data_repository import RawDataRecord, RssDataRepository
from linkurator_core.infrastructure.rss.rss_feed_client import RssFeedClient, RssFeedInfo, RssFeedItem

RSS_PROVIDER_NAME = "rss"
RSS_PROVIDER_ALIAS = "RSS"
RSS_PROVIDER_VERSION = DEFAULT_ITEM_VERSION
RSS_REFRESH_PERIOD_MINUTES = 5


def _map_rss_feed_item_to_item(rss_item: RssFeedItem, subscription_id: uuid.UUID) -> Item:
    """Map RssFeedItem to domain Item."""
    return Item.new(
        uuid=uuid.uuid4(),
        subscription_uuid=subscription_id,
        name=rss_item.title,
        description=rss_item.description,
        url=parse_url(rss_item.link),
        thumbnail=parse_url(rss_item.thumbnail),
        published_at=rss_item.published,
        provider=RSS_PROVIDER_NAME,
        version=RSS_PROVIDER_VERSION,
        duration=None,  # RSS feeds typically don't have duration
    )


def _map_rss_feed_info_to_subscription(
    feed_info: RssFeedInfo,
    feed_url: str,
    subscription_id: uuid.UUID | None = None,
) -> Subscription:
    """Map RssFeedInfo to domain Subscription."""
    return Subscription.new(
        uuid=subscription_id or uuid.uuid4(),
        name=feed_info.title,
        provider=RSS_PROVIDER_NAME,
        url=parse_url(feed_url),
        thumbnail=parse_url(feed_info.thumbnail),
        description=feed_info.description,
        external_data={
            "feed_url": feed_url,
            "language": feed_info.language,
            "link": feed_info.link,
        },
    )


class RssSubscriptionService(SubscriptionService):
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        item_repository: ItemRepository,
        rss_feed_client: RssFeedClient,
        rss_data_repository: RssDataRepository,
    ) -> None:
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.rss_feed_client = rss_feed_client
        self.rss_data_repository = rss_data_repository

    def provider_name(self) -> ItemProvider:
        return RSS_PROVIDER_NAME

    def provider_alias(self) -> str:
        return RSS_PROVIDER_ALIAS

    def provider_version(self) -> int:
        return RSS_PROVIDER_VERSION

    def refresh_period_minutes(self) -> int:
        return RSS_REFRESH_PERIOD_MINUTES

    async def get_subscriptions(
        self,
        user_id: uuid.UUID,  # noqa: ARG002
        access_token: str,  # noqa: ARG002
        credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> list[Subscription]:
        """RSS feeds don't have user accounts, return empty list."""
        return []

    async def get_subscription(
        self,
        sub_id: uuid.UUID,
        credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> Subscription | None:
        """Get and update subscription information from RSS feed."""
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != self.provider_name():
            return None

        feed_url = subscription.external_data.get("feed_url")
        if feed_url is None:
            return None

        return await self.get_subscription_from_url(parse_url(feed_url))

    async def get_subscription_items(
        self,
        sub_id: uuid.UUID,
        from_date: datetime,
        credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> list[Item]:
        """Get items from RSS feed published after from_date."""
        subscription = await self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != self.provider_name():
            return []

        feed_url = subscription.external_data.get("feed_url")
        if not feed_url:
            return []

        try:
            rss_items = [rss_item for rss_item
                         in await self.rss_feed_client.get_feed_items(feed_url)
                         if rss_item.published > from_date]

            rss_items = await self.rss_feed_client.get_feed_items_with_thumbnails(rss_items)

            # Filter items published after from_date and convert to domain Items
            items: list[Item] = []
            raw_data_records: list[RawDataRecord] = []
            for rss_item in rss_items:
                item = _map_rss_feed_item_to_item(rss_item, sub_id)
                items.append(item)

                # Store raw RSS data in repository
                raw_data_record = RawDataRecord(
                    rss_url=feed_url,
                    item_url=rss_item.link,
                    raw_data=rss_item.raw_data,
                )
                raw_data_records.append(raw_data_record)

            await self.rss_data_repository.set_raw_data(raw_data_records)

            return items

        except InvalidRssFeedError as e:
            logging.exception("Error fetching RSS feed items %s: %s", feed_url, e)
            return []

    async def get_items(
        self,
        item_ids: set[uuid.UUID],
        credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> set[Item]:
        """
        Get specific items by ID from cached raw RSS data.

        Retrieves items from RssDataRepository and parses them.
        If raw data is not available, returns empty set for those items.
        """
        # Fetch items from repository to get their URLs and subscriptions
        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(item_ids=item_ids),
            page_number=0,
            limit=len(item_ids),
        )

        # Filter for RSS items only
        rss_items = [item for item in items if item.provider == self.provider_name()]

        updated_items: set[Item] = set()

        for item in rss_items:
            # Get subscription to find feed_url
            subscription = await self.subscription_repository.get(item.subscription_uuid)
            if subscription is None or subscription.provider != self.provider_name():
                continue

            feed_url = subscription.external_data.get("feed_url")
            if not feed_url:
                continue

            # Get raw data from repository
            raw_data = await self.rss_data_repository.get_raw_data(feed_url, str(item.url))
            if not raw_data:
                continue

            try:
                # Parse the raw XML data
                root = ET.fromstring(raw_data)

                # Detect feed type and parse item
                if root.tag == "rss":
                    rss_feed_items = self.rss_feed_client._parse_rss_items(root)
                elif root.tag == "{http://www.w3.org/2005/Atom}feed":
                    rss_feed_items = self.rss_feed_client._parse_atom_items(root)
                else:
                    logging.warning("Unknown feed format for item %s: %s", item.uuid, root.tag)
                    continue

                # There should be exactly one item in the parsed result
                if len(rss_feed_items) == 1:
                    rss_feed_item = rss_feed_items[0]
                    # Create updated item preserving the original UUID
                    updated_item = Item.new(
                        uuid=item.uuid,
                        subscription_uuid=item.subscription_uuid,
                        name=rss_feed_item.title,
                        description=rss_feed_item.description,
                        url=parse_url(rss_feed_item.link),
                        thumbnail=parse_url(rss_feed_item.thumbnail),
                        published_at=rss_feed_item.published,
                        provider=self.provider_name(),
                        version=self.provider_version(),
                        duration=None,
                    )
                    updated_items.add(updated_item)

            except ET.ParseError as e:
                logging.exception("Failed to parse raw XML for item %s: %s", item.uuid, e)
                continue
            except Exception as e:
                logging.exception("Error processing item %s: %s", item.uuid, e)
                continue

        return updated_items

    async def get_subscription_from_url(
        self,
        url: AnyUrl,
        credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> Subscription | None:
        """
        Get or create subscription from URL.

        Supports:
        1. Direct RSS feed URL
        """
        url_str = str(url)
        try:
            feed_info = await self.rss_feed_client.get_feed_info(url_str)
        except InvalidRssFeedError as e:
            logging.exception("Error fetching discovered RSS feed %s: %s", url_str, e)
            return None

        # Check if subscription already exists
        new_sub = _map_rss_feed_info_to_subscription(feed_info, url_str)
        existing_sub = await self.subscription_repository.find_by_url(url)
        if existing_sub is not None:
            existing_sub.thumbnail = new_sub.thumbnail
            existing_sub.description = new_sub.description
            existing_sub.name = new_sub.name
            existing_sub.external_data = new_sub.external_data
            return existing_sub

        return new_sub

    async def get_subscriptions_from_name(
        self,
        name: str,  # noqa: ARG002
        credential: ExternalServiceCredential | None = None,  # noqa: ARG002
    ) -> list[Subscription]:
        """
        Search for RSS feeds by name.

        Phase 1: Not implemented (requires external search API).
        Users should provide direct URLs instead.
        """
        return []
