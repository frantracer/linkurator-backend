from ipaddress import IPv4Address
from typing import Any
from uuid import uuid4

import pytest

from linkurator_core.infrastructure.in_memory.rss_data_repository import InMemoryRssDataRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.rss_data_repository import MongoDBRssDataRepository
from linkurator_core.infrastructure.rss.rss_data_repository import RawDataRecord, RssDataRepository


@pytest.fixture(name="rss_data_repo", scope="session", params=["mongodb", "in_memory"])
def fixture_rss_data_repo(db_name: str, request: Any) -> RssDataRepository:
    if request.param == "mongodb":
        return MongoDBRssDataRepository(
            IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop",
        )
    return InMemoryRssDataRepository()


@pytest.mark.asyncio()
async def test_exception_is_raised_if_rss_data_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBRssDataRepository(
            IPv4Address("127.0.0.1"), 27017, non_existent_db_name, "develop", "develop",
        )
        await repo.check_connection()


@pytest.mark.asyncio()
async def test_get_nonexistent_raw_data(rss_data_repo: RssDataRepository) -> None:
    """Test retrieving raw data that doesn't exist returns None."""
    result = await rss_data_repo.get_raw_data(
        "https://nonexistent.com/feed.xml", "https://nonexistent.com/item",
    )

    assert result is None


@pytest.mark.asyncio()
async def test_set_multiple_raw_data_records(rss_data_repo: RssDataRepository) -> None:
    """Test storing multiple raw data records at once."""
    records = [
        RawDataRecord(
            rss_url="https://example.com/feed.xml",
            item_url="https://example.com/item1",
            raw_data="<item><title>First</title></item>",
        ),
        RawDataRecord(
            rss_url="https://example.com/feed.xml",
            item_url="https://example.com/item2",
            raw_data="<item><title>Second</title></item>",
        ),
        RawDataRecord(
            rss_url="https://example.com/feed.xml",
            item_url="https://example.com/item3",
            raw_data="<item><title>Third</title></item>",
        ),
    ]

    await rss_data_repo.set_raw_data(records)

    # Verify all records were stored
    for record in records:
        result = await rss_data_repo.get_raw_data(record.rss_url, record.item_url)
        assert result == record.raw_data


@pytest.mark.asyncio()
async def test_update_existing_raw_data(rss_data_repo: RssDataRepository) -> None:
    """Test updating an existing raw data record."""
    rss_url = "https://example.com/feed.xml"
    item_url = "https://example.com/item1"

    # Store initial data
    initial_record = RawDataRecord(
        rss_url=rss_url,
        item_url=item_url,
        raw_data="<item><title>Initial</title></item>",
    )
    await rss_data_repo.set_raw_data([initial_record])

    # Update with new data
    updated_record = RawDataRecord(
        rss_url=rss_url,
        item_url=item_url,
        raw_data="<item><title>Updated</title></item>",
    )
    await rss_data_repo.set_raw_data([updated_record])

    # Verify the data was updated
    result = await rss_data_repo.get_raw_data(rss_url, item_url)
    assert result == updated_record.raw_data


@pytest.mark.asyncio()
async def test_different_feeds_same_item_url(rss_data_repo: RssDataRepository) -> None:
    """Test that different feeds can have items with the same URL."""
    item_url = "https://example.com/item"
    records = [
        RawDataRecord(
            rss_url="https://feed1.com/feed.xml",
            item_url=item_url,
            raw_data="<item>Feed 1 data</item>",
        ),
        RawDataRecord(
            rss_url="https://feed2.com/feed.xml",
            item_url=item_url,
            raw_data="<item>Feed 2 data</item>",
        ),
    ]

    await rss_data_repo.set_raw_data(records)

    # Verify each feed's data is stored separately
    result1 = await rss_data_repo.get_raw_data(records[0].rss_url, item_url)
    result2 = await rss_data_repo.get_raw_data(records[1].rss_url, item_url)

    assert result1 == records[0].raw_data
    assert result2 == records[1].raw_data


@pytest.mark.asyncio()
async def test_raw_data_with_special_characters(rss_data_repo: RssDataRepository) -> None:
    """Test storing and retrieving raw data with special characters and unicode."""
    record = RawDataRecord(
        rss_url="https://example.com/feed.xml",
        item_url="https://example.com/item",
        raw_data='<item><title>Test with "quotes" & symbols: €, ñ, 中文, 🎉</title></item>',
    )

    await rss_data_repo.set_raw_data([record])
    result = await rss_data_repo.get_raw_data(record.rss_url, record.item_url)

    assert result == record.raw_data


@pytest.mark.asyncio()
async def test_raw_data_with_newlines_and_formatting(rss_data_repo: RssDataRepository) -> None:
    """Test that XML formatting (newlines, indentation) is preserved."""
    record = RawDataRecord(
        rss_url="https://example.com/feed.xml",
        item_url="https://example.com/item",
        raw_data="""<rss version="2.0">
    <channel>
        <item>
            <title>Test</title>
            <description>Description</description>
        </item>
    </channel>
</rss>""",
    )

    await rss_data_repo.set_raw_data([record])
    result = await rss_data_repo.get_raw_data(record.rss_url, record.item_url)

    assert result == record.raw_data


@pytest.mark.asyncio()
async def test_empty_raw_data(rss_data_repo: RssDataRepository) -> None:
    """Test storing and retrieving empty raw data."""
    record = RawDataRecord(
        rss_url="https://example.com/feed.xml",
        item_url="https://example.com/item",
        raw_data="",
    )

    await rss_data_repo.set_raw_data([record])
    result = await rss_data_repo.get_raw_data(record.rss_url, record.item_url)

    assert result == ""
