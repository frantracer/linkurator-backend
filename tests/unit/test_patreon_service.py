import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from pydantic import AnyUrl

from linkurator_core.domain.common.mock_factory import mock_item, mock_sub
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.patreon.patreon_api_client import (
    PatreonApiClient,
    PatreonAvatarPhotoImageUrls,
    PatreonCampaign,
    PatreonMembership,
    PatreonPost,
)
from linkurator_core.infrastructure.patreon.patreon_service import (
    CAMPAIGN_ID_KEY,
    DEFAULT_PATREON_ICON,
    VANITY_KEY,
    PatreonSubscriptionService,
    extract_post_id_from_url,
    extract_vanity_from_url,
    map_patreon_campaign_to_subscription,
    map_patreon_post_to_item,
)


def _make_campaign(
        campaign_id: str = "123",
        vanity: str = "creator",
        creation_name: str = "My Creation",
        summary: str = "A summary",
        url: str = "https://www.patreon.com/creator",
        avatar_url: str = "https://example.com/avatar.png",
) -> PatreonCampaign:
    return PatreonCampaign(
        id=campaign_id,
        creation_name=creation_name,
        summary=summary,
        url=url,
        vanity=vanity,
        avatar_photo_image_urls=PatreonAvatarPhotoImageUrls(default=AnyUrl(avatar_url)),
    )


def _make_post(
        post_id: str = "post-1",
        title: str = "Test Post",
        url: str = "https://www.patreon.com/posts/test-post-12345",
        published_at: datetime | None = None,
        image_url: str | None = "https://example.com/image.png",
        duration_seconds: int | None = None,
) -> PatreonPost:
    return PatreonPost(
        id=post_id,
        title=title,
        url=url,
        published_at=published_at or datetime(2024, 1, 1, tzinfo=timezone.utc),
        image_url=image_url,
        duration_seconds=duration_seconds,
    )


# =============================================================================
# Tests for map_patreon_post_to_item
# =============================================================================

class TestMapPatreonPostToItem:
    def test_maps_post_fields_to_item(self) -> None:
        sub_id = uuid.uuid4()
        post = _make_post(
            title="My Post",
            url="https://www.patreon.com/posts/my-post-999",
            published_at=datetime(2024, 6, 15, tzinfo=timezone.utc),
            image_url="https://example.com/thumb.png",
            duration_seconds=120,
        )

        item = map_patreon_post_to_item(post, sub_id)

        assert item.name == "My Post"
        assert str(item.url) == "https://www.patreon.com/posts/my-post-999"
        assert item.published_at == datetime(2024, 6, 15, tzinfo=timezone.utc)
        assert str(item.thumbnail) == "https://example.com/thumb.png"
        assert item.subscription_uuid == sub_id
        assert item.duration == 120
        assert item.provider == "patreon"

    def test_uses_default_icon_when_no_image(self) -> None:
        post = _make_post(image_url=None)

        item = map_patreon_post_to_item(post, uuid.uuid4())

        assert str(item.thumbnail) == DEFAULT_PATREON_ICON

    def test_duration_is_none_when_not_provided(self) -> None:
        post = _make_post(duration_seconds=None)

        item = map_patreon_post_to_item(post, uuid.uuid4())

        assert item.duration is None


# =============================================================================
# Tests for map_patreon_campaign_to_subscription
# =============================================================================

class TestMapPatreonCampaignToSubscription:
    def test_creates_new_subscription_from_campaign(self) -> None:
        campaign = _make_campaign(
            campaign_id="c-456",
            vanity="some_creator",
            summary="Creator summary",
            url="https://www.patreon.com/some_creator",
        )

        sub = map_patreon_campaign_to_subscription(campaign)

        assert sub.name == "some_creator"
        assert str(sub.url) == "https://www.patreon.com/some_creator"
        assert sub.description == "Creator summary"
        assert sub.provider == "patreon"
        assert sub.external_data[VANITY_KEY] == "some_creator"
        assert sub.external_data[CAMPAIGN_ID_KEY] == "c-456"

    def test_uses_campaign_avatar_as_thumbnail(self) -> None:
        campaign = _make_campaign(avatar_url="https://example.com/my_avatar.png")

        sub = map_patreon_campaign_to_subscription(campaign)

        assert str(sub.thumbnail) == "https://example.com/my_avatar.png"

    def test_updates_existing_subscription(self) -> None:
        existing = mock_sub(provider="patreon", name="old_name")
        campaign = _make_campaign(
            campaign_id="c-789",
            vanity="new_name",
            creation_name="Creation",
            summary="New summary",
        )

        updated = map_patreon_campaign_to_subscription(campaign, existing)

        assert updated.uuid == existing.uuid
        assert updated.name == "new_name"
        assert updated.description == "Creation - New summary"
        assert updated.external_data[VANITY_KEY] == "new_name"
        assert updated.external_data[CAMPAIGN_ID_KEY] == "c-789"

    def test_updates_existing_subscription_without_mutating_original(self) -> None:
        existing = mock_sub(provider="patreon", name="original")
        campaign = _make_campaign(vanity="modified")

        map_patreon_campaign_to_subscription(campaign, existing)

        assert existing.name == "original"

    def test_empty_summary_uses_empty_string(self) -> None:
        campaign = _make_campaign(summary="")

        sub = map_patreon_campaign_to_subscription(campaign)

        assert sub.description == ""


# =============================================================================
# Tests for extract_campaign_id_from_url
# =============================================================================

class TestExtractCampaignIdFromUrl:
    def test_extracts_vanity_from_simple_url(self) -> None:
        assert extract_vanity_from_url(parse_url("https://www.patreon.com/creator")) == "creator"

    def test_extracts_vanity_from_c_url(self) -> None:
        assert extract_vanity_from_url(parse_url("https://www.patreon.com/c/mycreator")) == "mycreator"

    def test_returns_none_for_non_patreon_url(self) -> None:
        assert extract_vanity_from_url(parse_url("https://www.youtube.com/channel/123")) is None

    def test_returns_none_for_empty_path(self) -> None:
        assert extract_vanity_from_url(parse_url("https://www.patreon.com/")) is None

    def test_works_without_www(self) -> None:
        assert extract_vanity_from_url(parse_url("https://patreon.com/creator")) == "creator"

    def test_ignores_query_params(self) -> None:
        assert extract_vanity_from_url(parse_url("https://www.patreon.com/creator?l=es")) == "creator"

    def test_extracts_vanity_from_cw_url(self) -> None:
        assert extract_vanity_from_url(parse_url("https://www.patreon.com/cw/naroh")) == "naroh"


# =============================================================================
# Tests for extract_post_id_from_url
# =============================================================================

class TestExtractPostIdFromUrl:
    def test_extracts_id_from_post_url_with_title(self) -> None:
        assert extract_post_id_from_url(parse_url("https://www.patreon.com/posts/my-post-12345")) == "12345"

    def test_extracts_id_from_post_url_without_title(self) -> None:
        assert extract_post_id_from_url(parse_url("https://www.patreon.com/posts/12345")) == "12345"

    def test_returns_none_for_non_post_url(self) -> None:
        assert extract_post_id_from_url(parse_url("https://www.patreon.com/creator")) is None

    def test_returns_none_for_non_patreon_url(self) -> None:
        assert extract_post_id_from_url(parse_url("https://www.youtube.com/posts/12345")) is None


# =============================================================================
# Tests for PatreonSubscriptionService
# =============================================================================

def _make_service(
        patreon_client: PatreonApiClient | None = None,
        subscription_repository: InMemorySubscriptionRepository | None = None,
        item_repository: InMemoryItemRepository | None = None,
) -> PatreonSubscriptionService:
    return PatreonSubscriptionService(
        subscription_repository=subscription_repository or InMemorySubscriptionRepository(),
        item_repository=item_repository or InMemoryItemRepository(),
        patreon_client=patreon_client or AsyncMock(spec=PatreonApiClient),
    )


class TestPatreonSubscriptionServiceProperties:
    def test_provider_name(self) -> None:
        service = _make_service()
        assert service.provider_name() == "patreon"

    def test_provider_alias(self) -> None:
        service = _make_service()
        assert service.provider_alias() == "Patreon"

    def test_refresh_period_minutes(self) -> None:
        service = _make_service()
        assert service.refresh_period_minutes() == 60

    def test_provider_thumbnail(self) -> None:
        service = _make_service()
        assert service.provider_thumbnail() == DEFAULT_PATREON_ICON


class TestGetSubscriptions:
    @pytest.mark.asyncio()
    async def test_returns_subscriptions_for_user_memberships(self) -> None:
        client = AsyncMock(spec=PatreonApiClient)
        client.get_current_user_memberships.return_value = [
            PatreonMembership(campaign_id="c1"),
            PatreonMembership(campaign_id="c2"),
        ]
        campaign1 = _make_campaign(campaign_id="c1", vanity="creator1")
        campaign2 = _make_campaign(campaign_id="c2", vanity="creator2")
        client.get_campaign.side_effect = {
            "c1": campaign1, "c2": campaign2,
        }.get

        service = _make_service(patreon_client=client)
        subs = await service.get_subscriptions(user_id=uuid.uuid4(), access_token="token")

        assert len(subs) == 2
        assert subs[0].name == "creator1"
        assert subs[1].name == "creator2"

    @pytest.mark.asyncio()
    async def test_skips_campaigns_that_are_not_found(self) -> None:
        client = AsyncMock(spec=PatreonApiClient)
        client.get_current_user_memberships.return_value = [
            PatreonMembership(campaign_id="c1"),
            PatreonMembership(campaign_id="missing"),
        ]
        client.get_campaign.side_effect = lambda cid: _make_campaign(campaign_id="c1") if cid == "c1" else None

        service = _make_service(patreon_client=client)
        subs = await service.get_subscriptions(user_id=uuid.uuid4(), access_token="token")

        assert len(subs) == 1

    @pytest.mark.asyncio()
    async def test_returns_empty_when_no_memberships(self) -> None:
        client = AsyncMock(spec=PatreonApiClient)
        client.get_current_user_memberships.return_value = []

        service = _make_service(patreon_client=client)
        subs = await service.get_subscriptions(user_id=uuid.uuid4(), access_token="token")

        assert subs == []


class TestGetSubscription:
    @pytest.mark.asyncio()
    async def test_returns_updated_subscription(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        existing = mock_sub(provider="patreon", external_data={CAMPAIGN_ID_KEY: "c1", VANITY_KEY: "old"})
        await sub_repo.add(existing)

        campaign = _make_campaign(campaign_id="c1", vanity="new_name")
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign.return_value = campaign

        service = _make_service(patreon_client=client, subscription_repository=sub_repo)
        result = await service.get_subscription(existing.uuid)

        assert result is not None
        assert result.uuid == existing.uuid
        assert result.name == "new_name"

    @pytest.mark.asyncio()
    async def test_returns_none_for_non_existing_subscription(self) -> None:
        service = _make_service()
        result = await service.get_subscription(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_for_non_patreon_subscription(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        youtube_sub = mock_sub(provider="youtube")
        await sub_repo.add(youtube_sub)

        service = _make_service(subscription_repository=sub_repo)
        result = await service.get_subscription(youtube_sub.uuid)
        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_when_no_campaign_id(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        sub = mock_sub(provider="patreon", external_data={})
        await sub_repo.add(sub)

        service = _make_service(subscription_repository=sub_repo)
        result = await service.get_subscription(sub.uuid)
        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_when_campaign_not_found(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        sub = mock_sub(provider="patreon", external_data={CAMPAIGN_ID_KEY: "gone"})
        await sub_repo.add(sub)

        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign.return_value = None

        service = _make_service(patreon_client=client, subscription_repository=sub_repo)
        result = await service.get_subscription(sub.uuid)
        assert result is None


class TestGetSubscriptionItems:
    @pytest.mark.asyncio()
    async def test_returns_items_from_campaign_posts(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        sub = mock_sub(provider="patreon", external_data={CAMPAIGN_ID_KEY: "c1"})
        await sub_repo.add(sub)

        post = _make_post(title="New Video")
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_posts.return_value = [post]

        service = _make_service(patreon_client=client, subscription_repository=sub_repo)
        from_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        items = await service.get_subscription_items(sub.uuid, from_date)

        assert len(items) == 1
        assert items[0].name == "New Video"
        assert items[0].subscription_uuid == sub.uuid
        client.get_campaign_posts.assert_called_once_with("c1", from_date)

    @pytest.mark.asyncio()
    async def test_returns_empty_for_non_existing_subscription(self) -> None:
        service = _make_service()
        items = await service.get_subscription_items(uuid.uuid4(), datetime.now(timezone.utc))
        assert items == []

    @pytest.mark.asyncio()
    async def test_returns_empty_for_non_patreon_subscription(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        sub = mock_sub(provider="youtube")
        await sub_repo.add(sub)

        service = _make_service(subscription_repository=sub_repo)
        items = await service.get_subscription_items(sub.uuid, datetime.now(timezone.utc))
        assert items == []

    @pytest.mark.asyncio()
    async def test_returns_empty_when_no_campaign_id(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        sub = mock_sub(provider="patreon", external_data={})
        await sub_repo.add(sub)

        service = _make_service(subscription_repository=sub_repo)
        items = await service.get_subscription_items(sub.uuid, datetime.now(timezone.utc))
        assert items == []


class TestGetItems:
    @pytest.mark.asyncio()
    async def test_fetches_and_updates_items_from_api(self) -> None:
        item_repo = InMemoryItemRepository()
        item = mock_item(
            provider="patreon",
            url="https://www.patreon.com/posts/my-post-55555",
        )
        await item_repo.upsert_items([item])

        updated_post = _make_post(title="Updated Title", url="https://www.patreon.com/posts/my-post-55555")
        client = AsyncMock(spec=PatreonApiClient)
        client.get_post.return_value = updated_post

        service = _make_service(patreon_client=client, item_repository=item_repo)
        result = await service.get_items({item.uuid})

        assert len(result) == 1
        updated_item = next(iter(result))
        assert updated_item.name == "Updated Title"
        assert updated_item.uuid == item.uuid
        assert updated_item.created_at == item.created_at

    @pytest.mark.asyncio()
    async def test_skips_items_without_post_id(self) -> None:
        item_repo = InMemoryItemRepository()
        item = mock_item(provider="patreon", url="https://www.patreon.com/creator")
        await item_repo.upsert_items([item])

        client = AsyncMock(spec=PatreonApiClient)
        service = _make_service(patreon_client=client, item_repository=item_repo)
        result = await service.get_items({item.uuid})

        assert len(result) == 0
        client.get_post.assert_not_called()

    @pytest.mark.asyncio()
    async def test_skips_items_when_post_not_found(self) -> None:
        item_repo = InMemoryItemRepository()
        item = mock_item(provider="patreon", url="https://www.patreon.com/posts/gone-99999")
        await item_repo.upsert_items([item])

        client = AsyncMock(spec=PatreonApiClient)
        client.get_post.return_value = None

        service = _make_service(patreon_client=client, item_repository=item_repo)
        result = await service.get_items({item.uuid})

        assert len(result) == 0


class TestGetSubscriptionFromUrl:
    @pytest.mark.asyncio()
    async def test_returns_new_subscription_from_campaign(self) -> None:
        campaign = _make_campaign(campaign_id="123", vanity="creator")
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_id_from_vanity.return_value = "123"
        client.get_campaign.return_value = campaign

        service = _make_service(patreon_client=client)
        result = await service.get_subscription_from_url(parse_url("https://www.patreon.com/creator"))

        assert result is not None
        assert result.name == "creator"

    @pytest.mark.asyncio()
    async def test_updates_existing_subscription_when_found(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        existing = mock_sub(provider="patreon", url="https://www.patreon.com/creator")
        await sub_repo.add(existing)

        campaign = _make_campaign(campaign_id="123", vanity="creator_new")
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_id_from_vanity.return_value = "123"
        client.get_campaign.return_value = campaign

        service = _make_service(patreon_client=client, subscription_repository=sub_repo)
        result = await service.get_subscription_from_url(parse_url("https://www.patreon.com/creator"))

        assert result is not None
        assert result.uuid == existing.uuid
        assert result.name == "creator_new"

    @pytest.mark.asyncio()
    async def test_returns_existing_when_campaign_not_found(self) -> None:
        sub_repo = InMemorySubscriptionRepository()
        existing = mock_sub(provider="patreon", url="https://www.patreon.com/creator")
        await sub_repo.add(existing)

        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_id_from_vanity.return_value = "123"
        client.get_campaign.return_value = PatreonCampaign(
            id="123",
            vanity="creator",
            creation_name="Creation",
            summary="Summary",
            url="https://www.patreon.com/creator",
            avatar_photo_image_urls=PatreonAvatarPhotoImageUrls(default=AnyUrl("https://example.com/avatar.png")),
        )

        service = _make_service(patreon_client=client, subscription_repository=sub_repo)
        result = await service.get_subscription_from_url(parse_url("https://www.patreon.com/creator"))

        assert result is not None
        assert result.uuid == existing.uuid

    @pytest.mark.asyncio()
    async def test_returns_none_for_non_patreon_url(self) -> None:
        service = _make_service()
        result = await service.get_subscription_from_url(parse_url("https://www.youtube.com/channel/123"))
        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_when_campaign_id_not_found(self) -> None:
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_id_from_vanity.return_value = None

        service = _make_service(patreon_client=client)
        result = await service.get_subscription_from_url(parse_url("https://www.patreon.com/unknown"))

        assert result is None
        client.get_campaign.assert_not_called()

    @pytest.mark.asyncio()
    async def test_returns_none_when_no_campaign_and_no_existing(self) -> None:
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_id_from_vanity.return_value = "123"
        client.get_campaign.return_value = None

        service = _make_service(patreon_client=client)
        result = await service.get_subscription_from_url(parse_url("https://www.patreon.com/unknown"))
        assert result is None

    @pytest.mark.asyncio()
    async def test_uses_campaign_id_returned_by_vanity_lookup(self) -> None:
        campaign = _make_campaign(campaign_id="456", vanity="creator")
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_id_from_vanity.return_value = "456"
        client.get_campaign.return_value = campaign

        service = _make_service(patreon_client=client)
        await service.get_subscription_from_url(parse_url("https://www.patreon.com/creator"))

        client.get_campaign_id_from_vanity.assert_called_once_with("creator")
        client.get_campaign.assert_called_once_with("456")

    @pytest.mark.asyncio()
    async def test_works_with_c_path_url(self) -> None:
        campaign = _make_campaign(campaign_id="789", vanity="mycreator")
        client = AsyncMock(spec=PatreonApiClient)
        client.get_campaign_id_from_vanity.return_value = "789"
        client.get_campaign.return_value = campaign

        service = _make_service(patreon_client=client)
        result = await service.get_subscription_from_url(parse_url("https://www.patreon.com/c/mycreator"))

        assert result is not None
        assert result.name == "mycreator"
        client.get_campaign_id_from_vanity.assert_called_once_with("mycreator")


class TestGetSubscriptionsFromName:
    @pytest.mark.asyncio()
    async def test_always_returns_empty_list(self) -> None:
        service = _make_service()
        result = await service.get_subscriptions_from_name("anything")
        assert result == []
