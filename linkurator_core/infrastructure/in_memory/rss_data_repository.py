from linkurator_core.infrastructure.rss.rss_data_repository import RawDataRecord, RssDataRepository


class InMemoryRssDataRepository(RssDataRepository):
    """In-memory implementation of RssDataRepository for testing."""

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[tuple[str, str], str] = {}

    async def set_raw_data(self, records: list[RawDataRecord]) -> None:
        """Store raw RSS data."""
        for record in records:
            key = (record.rss_url, record.item_url)
            self._data[key] = record.raw_data

    async def get_raw_data(self, rss_url: str, item_url: str) -> str | None:
        """Retrieve raw RSS data."""
        key = (rss_url, item_url)
        return self._data.get(key)
