from datetime import timedelta
from uuid import uuid4

import pytest

from linkurator_core.application.items.get_favorite_topics_items_handler import GetFavoriteTopicsItemsHandler
from linkurator_core.domain.common.mock_factory import mock_interaction, mock_item, mock_sub, mock_topic, mock_user
from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


def make_handler(
    topic_repo: InMemoryTopicRepository,
    sub_repo: InMemorySubscriptionRepository,
    item_repo: InMemoryItemRepository,
    user_repo: InMemoryUserRepository,
) -> GetFavoriteTopicsItemsHandler:
    return GetFavoriteTopicsItemsHandler(
        topic_repository=topic_repo,
        subscription_repository=sub_repo,
        item_repository=item_repo,
        user_repository=user_repo,
    )


@pytest.mark.asyncio()
async def test_get_favorite_topics_items_returns_items_from_favorite_topics() -> None:
    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)
    topic = mock_topic(subscription_uuids=[sub.uuid])
    user = mock_user(favorite_topics={topic.uuid})

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = make_handler(topic_repo, sub_repo, item_repo, user_repo)
    items = await handler.handle(
        user_id=user.uuid,
        created_before=item.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert len(items) == 1
    assert items[0] == ItemWithInteractions(
        item=item,
        subscription=sub,
        interactions=[],
    )


@pytest.mark.asyncio()
async def test_get_favorite_topics_items_returns_empty_when_user_not_found() -> None:
    user_repo = InMemoryUserRepository()
    handler = make_handler(
        InMemoryTopicRepository(),
        InMemorySubscriptionRepository(),
        InMemoryItemRepository(),
        user_repo,
    )

    items = await handler.handle(
        user_id=uuid4(),
        created_before=None,  # type: ignore[arg-type]
        page_number=0,
        page_size=10,
    )

    assert items == []


@pytest.mark.asyncio()
async def test_get_favorite_topics_items_returns_empty_when_no_favorite_topics() -> None:
    user = mock_user(favorite_topics=set())
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = make_handler(
        InMemoryTopicRepository(),
        InMemorySubscriptionRepository(),
        InMemoryItemRepository(),
        user_repo,
    )

    items = await handler.handle(
        user_id=user.uuid,
        created_before=None,  # type: ignore[arg-type]
        page_number=0,
        page_size=10,
    )

    assert items == []


@pytest.mark.asyncio()
async def test_get_favorite_topics_items_merges_subscriptions_from_multiple_topics() -> None:
    sub1 = mock_sub()
    sub2 = mock_sub()
    item1 = mock_item(sub_uuid=sub1.uuid)
    item2 = mock_item(sub_uuid=sub2.uuid)
    topic1 = mock_topic(subscription_uuids=[sub1.uuid])
    topic2 = mock_topic(subscription_uuids=[sub2.uuid])
    user = mock_user(favorite_topics={topic1.uuid, topic2.uuid})

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub1)
    await sub_repo.add(sub2)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item1, item2])

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic1)
    await topic_repo.add(topic2)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = make_handler(topic_repo, sub_repo, item_repo, user_repo)
    items = await handler.handle(
        user_id=user.uuid,
        created_before=max(item1.created_at, item2.created_at) + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert len(items) == 2
    item_uuids = {i.item.uuid for i in items}
    assert item1.uuid in item_uuids
    assert item2.uuid in item_uuids


@pytest.mark.asyncio()
async def test_get_favorite_topics_items_includes_user_interactions() -> None:
    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)
    topic = mock_topic(subscription_uuids=[sub.uuid])
    user = mock_user(favorite_topics={topic.uuid})
    interaction = mock_interaction(item_id=item.uuid, user_id=user.uuid)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(interaction)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = make_handler(topic_repo, sub_repo, item_repo, user_repo)
    items = await handler.handle(
        user_id=user.uuid,
        created_before=item.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert len(items) == 1
    assert items[0].interactions == [interaction]


@pytest.mark.asyncio()
async def test_get_favorite_topics_items_includes_curator_interactions() -> None:
    curator = mock_user()
    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)
    topic = mock_topic(subscription_uuids=[sub.uuid])
    user = mock_user(favorite_topics={topic.uuid}, curators={curator.uuid})
    curator_interaction = mock_interaction(item_id=item.uuid, user_id=curator.uuid,
                                           interaction_type=InteractionType.RECOMMENDED)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(curator_interaction)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    handler = make_handler(topic_repo, sub_repo, item_repo, user_repo)
    items = await handler.handle(
        user_id=user.uuid,
        created_before=item.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert len(items) == 1
    assert len(items[0].curator_interactions) == 1
    assert items[0].curator_interactions[0].curator == curator
    assert items[0].curator_interactions[0].interactions[0].type == InteractionType.RECOMMENDED


@pytest.mark.asyncio()
async def test_get_favorite_topics_items_with_excluded_subscriptions() -> None:
    sub1 = mock_sub()
    sub2 = mock_sub()
    item1 = mock_item(sub_uuid=sub1.uuid)
    item2 = mock_item(sub_uuid=sub2.uuid)
    topic = mock_topic(subscription_uuids=[sub1.uuid, sub2.uuid])
    user = mock_user(favorite_topics={topic.uuid})

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub1)
    await sub_repo.add(sub2)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item1, item2])

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = make_handler(topic_repo, sub_repo, item_repo, user_repo)
    items = await handler.handle(
        user_id=user.uuid,
        created_before=max(item1.created_at, item2.created_at) + timedelta(seconds=1),
        page_number=0,
        page_size=10,
        excluded_subscriptions={sub2.uuid},
    )

    assert len(items) == 1
    assert items[0].item.uuid == item1.uuid
