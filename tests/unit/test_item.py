from datetime import datetime, timedelta, timezone
from uuid import UUID

from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.item import Item


def test_new_sets_the_attributes() -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    past_published_at = fixed_now - timedelta(days=7)

    item = Item.new(
        uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
        subscription_uuid=UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b"),
        name="name",
        description="description",
        url=parse_url("https://example.com/item"),
        thumbnail=parse_url("https://example.com/thumb.png"),
        published_at=past_published_at,
        provider="rss",
        now_function=lambda: fixed_now,
    )

    assert item.uuid == UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6")
    assert item.subscription_uuid == UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")
    assert item.name == "name"
    assert item.description == "description"
    assert item.url == parse_url("https://example.com/item")
    assert item.thumbnail == parse_url("https://example.com/thumb.png")
    assert item.duration is None
    assert item.version == 0
    assert item.provider == "rss"
    assert item.created_at == fixed_now
    assert item.updated_at == fixed_now
    assert item.published_at == past_published_at
    assert item.deleted_at is None


def test_new_clamps_future_published_at_to_now() -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    future_published_at = fixed_now + timedelta(days=1)

    item = Item.new(
        uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
        subscription_uuid=UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b"),
        name="name",
        description="description",
        url=parse_url("https://example.com/item"),
        thumbnail=parse_url("https://example.com/thumb.png"),
        published_at=future_published_at,
        provider="rss",
        now_function=lambda: fixed_now,
    )

    assert item.published_at == fixed_now
