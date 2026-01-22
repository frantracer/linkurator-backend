from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from linkurator_core.domain.common.mock_factory import mock_item, mock_sub
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.patreon.patreon_api_client import PatreonApiClient, PatreonCampaign, PatreonPost
from linkurator_core.infrastructure.patreon.patreon_service import (
    PATREON_PROVIDER_NAME,
    PatreonSubscriptionService,
)


def create_mock_credential(access_token: str = "test_token") -> ExternalServiceCredential:  # noqa: S107
    return ExternalServiceCredential(
        user_id=uuid4(),
        credential_type=ExternalServiceType.PATREON_CREATOR_ACCESS_TOKEN,
        credential_value=access_token,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio()
async def test_get_subscriptions_returns_empty_without_token() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    subscriptions = await service.get_subscriptions(user_id=uuid4(), access_token="")
    assert subscriptions == []


@pytest.mark.asyncio()
async def test_get_subscriptions_returns_campaign_with_token() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)
    patreon_client.get_current_user_campaign.return_value = PatreonCampaign(
        id="123456",
        name="Test Creator",
        summary="Test description",
        image_url="https://example.com/image.png",
        url="https://www.patreon.com/testcreator",
        vanity="testcreator",
    )

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    credential = create_mock_credential()
    subscriptions = await service.get_subscriptions(user_id=uuid4(), access_token="", credential=credential)

    assert len(subscriptions) == 1
    assert subscriptions[0].name == "Test Creator"
    assert subscriptions[0].provider == PATREON_PROVIDER_NAME


@pytest.mark.asyncio()
async def test_get_subscription_updates_campaign_info() -> None:
    sub = mock_sub()
    sub.provider = PATREON_PROVIDER_NAME
    sub.external_data = {"campaign_id": "123456"}

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)
    patreon_client.get_campaign.return_value = PatreonCampaign(
        id="123456",
        name="Updated Creator Name",
        summary="Updated description",
        image_url="https://example.com/new-image.png",
        url="https://www.patreon.com/testcreator",
        vanity="testcreator",
    )

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    credential = create_mock_credential()
    updated_sub = await service.get_subscription(sub.uuid, credential=credential)

    assert updated_sub is not None
    assert updated_sub.name == "Updated Creator Name"
    assert updated_sub.description == "Updated description"
    patreon_client.get_campaign.assert_called_once_with("123456", "test_token")


@pytest.mark.asyncio()
async def test_get_subscription_returns_none_for_non_patreon() -> None:
    sub = mock_sub()
    sub.provider = "youtube"

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    result = await service.get_subscription(sub.uuid)
    assert result is None


@pytest.mark.asyncio()
async def test_get_subscription_returns_existing_without_token() -> None:
    sub = mock_sub()
    sub.provider = PATREON_PROVIDER_NAME
    sub.external_data = {"campaign_id": "123456"}

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    # Without credential, should return existing subscription unchanged
    result = await service.get_subscription(sub.uuid)
    assert result is not None
    assert result.uuid == sub.uuid


@pytest.mark.asyncio()
async def test_get_subscription_items_filters_by_date() -> None:
    sub = mock_sub()
    sub.provider = PATREON_PROVIDER_NAME
    sub.external_data = {"campaign_id": "123456"}

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)
    # Posts returned in descending order (newest first) as Patreon API typically does
    patreon_client.get_campaign_posts.return_value = (
        [
            PatreonPost(
                id="post2",
                title="New Post",
                content="New content",
                url="https://www.patreon.com/posts/new-post-222",
                published_at=datetime(2020, 1, 3, tzinfo=timezone.utc),
                image_url="https://example.com/image.png",
            ),
            PatreonPost(
                id="post1",
                title="Old Post",
                content="Old content",
                url="https://www.patreon.com/posts/old-post-111",
                published_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                image_url=None,
            ),
        ],
        None,  # No next cursor
    )

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    credential = create_mock_credential()
    items = await service.get_subscription_items(
        sub.uuid,
        from_date=datetime(2020, 1, 2, tzinfo=timezone.utc),
        credential=credential,
    )

    # Should only return the new post (after from_date)
    assert len(items) == 1
    assert items[0].name == "New Post"
    assert items[0].subscription_uuid == sub.uuid
    assert items[0].provider == PATREON_PROVIDER_NAME


@pytest.mark.asyncio()
async def test_get_subscription_items_returns_empty_without_token() -> None:
    sub = mock_sub()
    sub.provider = PATREON_PROVIDER_NAME
    sub.external_data = {"campaign_id": "123456"}

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    items = await service.get_subscription_items(
        sub.uuid,
        from_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )

    assert items == []


@pytest.mark.asyncio()
async def test_get_subscription_items_returns_empty_for_non_patreon() -> None:
    sub = mock_sub()
    sub.provider = "youtube"

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    credential = create_mock_credential()
    items = await service.get_subscription_items(
        sub.uuid,
        from_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        credential=credential,
    )

    assert items == []


@pytest.mark.asyncio()
async def test_get_items_returns_empty_without_token() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    items = await service.get_items(item_ids={uuid4()})
    assert items == set()


@pytest.mark.asyncio()
async def test_get_items_fetches_posts_by_id() -> None:
    sub = mock_sub()
    sub.provider = PATREON_PROVIDER_NAME

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item = mock_item(provider=PATREON_PROVIDER_NAME)
    item.subscription_uuid = sub.uuid
    item.url = parse_url("https://www.patreon.com/posts/test-post-12345")

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])

    patreon_client = AsyncMock(spec=PatreonApiClient)
    patreon_client.get_post.return_value = PatreonPost(
        id="12345",
        title="Updated Post Title",
        content="Updated content",
        url="https://www.patreon.com/posts/test-post-12345",
        published_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        image_url="https://example.com/image.png",
    )

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    credential = create_mock_credential()
    updated_items = await service.get_items(item_ids={item.uuid}, credential=credential)

    assert len(updated_items) == 1
    updated_item = next(iter(updated_items))
    assert updated_item.name == "Updated Post Title"
    patreon_client.get_post.assert_called_once_with("12345", "test_token")


@pytest.mark.asyncio()
async def test_get_subscription_from_url_creates_new_subscription_without_token() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    sub = await service.get_subscription_from_url(parse_url("https://www.patreon.com/creatorname"))

    assert sub is not None
    assert sub.name == "creatorname"  # Uses identifier as placeholder
    assert sub.provider == PATREON_PROVIDER_NAME
    assert sub.external_data["vanity"] == "creatorname"


@pytest.mark.asyncio()
async def test_get_subscription_from_url_with_api_details() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)
    patreon_client.get_campaign.return_value = PatreonCampaign(
        id="123456",
        name="Creator Name",
        summary="Creator description",
        image_url="https://example.com/image.png",
        url="https://www.patreon.com/creatorname",
        vanity="creatorname",
    )

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    credential = create_mock_credential()
    sub = await service.get_subscription_from_url(
        parse_url("https://www.patreon.com/creatorname"),
        credential=credential,
    )

    assert sub is not None
    assert sub.name == "Creator Name"
    assert sub.provider == PATREON_PROVIDER_NAME
    assert sub.external_data["campaign_id"] == "123456"


@pytest.mark.asyncio()
async def test_get_subscription_from_url_handles_c_path() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    sub = await service.get_subscription_from_url(parse_url("https://www.patreon.com/c/creatorname"))

    assert sub is not None
    assert sub.external_data["vanity"] == "creatorname"


@pytest.mark.asyncio()
async def test_get_subscription_from_url_updates_existing_subscription() -> None:
    existing_sub = mock_sub()
    existing_sub.provider = PATREON_PROVIDER_NAME
    existing_sub.url = parse_url("https://www.patreon.com/creatorname")

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(existing_sub)

    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)
    patreon_client.get_campaign.return_value = PatreonCampaign(
        id="123456",
        name="Updated Title",
        summary="Updated description",
        image_url="https://example.com/new-image.png",
        url="https://www.patreon.com/creatorname",
        vanity="creatorname",
    )

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    credential = create_mock_credential()
    sub = await service.get_subscription_from_url(
        parse_url("https://www.patreon.com/creatorname"),
        credential=credential,
    )

    assert sub is not None
    assert sub.uuid == existing_sub.uuid
    assert sub.name == "Updated Title"
    assert sub.description == "Updated description"


@pytest.mark.asyncio()
async def test_get_subscription_from_url_returns_none_for_non_patreon() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    sub = await service.get_subscription_from_url(parse_url("https://youtube.com/channel/123"))
    assert sub is None


@pytest.mark.asyncio()
async def test_get_subscriptions_from_name_returns_empty_list() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    subscriptions = await service.get_subscriptions_from_name("test")
    assert subscriptions == []


def test_provider_info() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    patreon_client = AsyncMock(spec=PatreonApiClient)

    service = PatreonSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        patreon_client=patreon_client,
    )

    assert service.provider_name() == "patreon"
    assert service.provider_alias() == "Patreon"
    assert service.refresh_period_minutes() == 60
