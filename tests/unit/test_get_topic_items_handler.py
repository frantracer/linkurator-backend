from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.common.mock_factory import mock_interaction, mock_item, mock_sub, mock_topic, mock_user
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository


@pytest.mark.asyncio()
async def test_get_topic_items_handler() -> None:
    user = mock_user()
    sub = mock_sub()
    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item1 = mock_item(sub_uuid=sub.uuid)
    interaction = mock_interaction(item_id=item1.uuid, user_id=user.uuid)
    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item1])
    await item_repo.add_interaction(interaction)

    topic1 = mock_topic(subscription_uuids=[sub.uuid], user_uuid=user.uuid)
    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic1)

    handler = GetTopicItemsHandler(
        topic_repository=topic_repo,
        subscription_repository=sub_repo,
        item_repository=item_repo,
    )
    items = await handler.handle(
        user_id=user.uuid,
        topic_id=topic1.uuid,
        created_before=item1.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert len(items) == 1
    assert items[0] == ItemWithInteractions(
        item=item1,
        subscription=sub,
        interactions=[interaction],
    )


@pytest.mark.asyncio()
async def test_get_topic_items_handler_not_found_topic_raises_exception() -> None:
    topic_repository = InMemoryTopicRepository()
    subscription_repository = InMemorySubscriptionRepository()
    item_repository = InMemoryItemRepository()

    handler = GetTopicItemsHandler(
        topic_repository=topic_repository,
        subscription_repository=subscription_repository,
        item_repository=item_repository)
    with pytest.raises(TopicNotFoundError):
        await handler.handle(
            user_id=UUID("98028b50-86c2-4d2f-8787-414f0f470d15"),
            topic_id=UUID("04d6483c-f24d-4077-a722-a6d6e3dc3d65"),
            created_before=datetime(2020, 1, 1, tzinfo=timezone.utc),
            page_number=0,
            page_size=10,
        )


@pytest.mark.asyncio()
async def test_get_topic_items_handler_with_excluded_subscriptions() -> None:
    user = mock_user()
    sub1 = mock_sub()
    sub2 = mock_sub()
    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub1)
    await sub_repo.add(sub2)

    item1 = mock_item(sub_uuid=sub1.uuid)
    item2 = mock_item(sub_uuid=sub2.uuid)
    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item1, item2])

    topic1 = mock_topic(subscription_uuids=[sub1.uuid, sub2.uuid], user_uuid=user.uuid)
    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic1)

    handler = GetTopicItemsHandler(
        topic_repository=topic_repo,
        subscription_repository=sub_repo,
        item_repository=item_repo,
    )
    items = await handler.handle(
        user_id=user.uuid,
        topic_id=topic1.uuid,
        created_before=item1.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
        excluded_subscriptions={sub2.uuid},
    )

    assert len(items) == 1
    assert items[0].item == item1
    assert items[0].subscription == sub1
    assert items[0].interactions == []
