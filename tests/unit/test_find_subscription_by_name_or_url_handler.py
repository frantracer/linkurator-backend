from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import AnyUrl

from linkurator_core.application.subscriptions.find_subscription_by_name_handler import \
    FindSubscriptionsByNameOrUrlHandler
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio
async def test_find_subscription_by_url() -> None:
    sub_repo = InMemorySubscriptionRepository()
    sub = Subscription.new(
        uuid=UUID("291e0e31-46d4-4d7e-a39c-5bfd632a72cb"),
        name="Test",
        provider=SubscriptionProvider.YOUTUBE,
        url=AnyUrl("https://www.youtube.com/channel/UC6ZFN9Tx6xh-skXCuRHCDpQ"),
        thumbnail=AnyUrl("https://i.ytimg.com/vi/4jNz0lG0k2U/maxresdefault.jpg"),
    )
    await sub_repo.add(sub)

    sub_service = AsyncMock(spec=SubscriptionService)
    sub_service.get_subscription_from_url.return_value = sub

    handler = FindSubscriptionsByNameOrUrlHandler(sub_repo, sub_service)

    found_subs = await handler.handle(str(sub.url))

    assert len(found_subs) == 1
    assert found_subs[0] == sub


@pytest.mark.asyncio
async def test_find_subscription_by_name() -> None:
    sub_repo = InMemorySubscriptionRepository()
    sub = Subscription.new(
        uuid=UUID("291e0e31-46d4-4d7e-a39c-5bfd632a72cb"),
        name="Test",
        provider=SubscriptionProvider.YOUTUBE,
        url=AnyUrl("https://www.youtube.com/channel/UC6ZFN9Tx6xh-skXCuRHCDpQ"),
        thumbnail=AnyUrl("https://i.ytimg.com/vi/4jNz0lG0k2U/maxresdefault.jpg"),
    )
    await sub_repo.add(sub)

    sub_service = AsyncMock(spec=SubscriptionService)
    sub_service.get_subscription_from_url.return_value = None

    handler = FindSubscriptionsByNameOrUrlHandler(sub_repo, sub_service)

    found_subs = await handler.handle(sub.name)

    assert len(found_subs) == 1
    assert found_subs[0] == sub


@pytest.mark.asyncio
async def test_find_subscription_by_url_is_added_to_repo_if_not_exists() -> None:
    sub_repo = InMemorySubscriptionRepository()
    sub = Subscription.new(
        uuid=UUID("291e0e31-46d4-4d7e-a39c-5bfd632a72cb"),
        name="Test",
        provider=SubscriptionProvider.YOUTUBE,
        url=AnyUrl("https://www.youtube.com/channel/UC6ZFN9Tx6xh-skXCuRHCDpQ"),
        thumbnail=AnyUrl("https://i.ytimg.com/vi/4jNz0lG0k2U/maxresdefault.jpg"),
    )

    sub_service = AsyncMock(spec=SubscriptionService)
    sub_service.get_subscription_from_url.return_value = sub

    handler = FindSubscriptionsByNameOrUrlHandler(sub_repo, sub_service)

    found_subs = await handler.handle(str(sub.url))

    assert len(found_subs) == 1
    assert found_subs[0] == sub

    assert await sub_repo.get(sub.uuid) == sub


@pytest.mark.asyncio
async def test_find_subscription_by_non_existing_name() -> None:
    sub_repo = InMemorySubscriptionRepository()
    sub_service = AsyncMock(spec=SubscriptionService)
    sub_service.get_subscription_from_url.return_value = None

    handler = FindSubscriptionsByNameOrUrlHandler(sub_repo, sub_service)

    found_subs = await handler.handle("Test")

    assert len(found_subs) == 0


@pytest.mark.asyncio
async def test_find_subscription_by_non_existing_url() -> None:
    sub_repo = InMemorySubscriptionRepository()
    sub_service = AsyncMock(spec=SubscriptionService)
    sub_service.get_subscription_from_url.return_value = None

    handler = FindSubscriptionsByNameOrUrlHandler(sub_repo, sub_service)

    found_subs = await handler.handle("https://www.youtube.com/channel/UC6ZFN9Tx6xh-skXCuRHCDpQ")

    assert len(found_subs) == 0
