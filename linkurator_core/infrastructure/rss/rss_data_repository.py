from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawDataRecord:
    rss_url: str
    item_url: str
    raw_data: str


class RssDataRepository(ABC):
    @abstractmethod
    async def set_raw_data(self, records: list[RawDataRecord]) -> None:
        ...

    @abstractmethod
    async def get_raw_data(self, rss_url: str, item_url: str) -> str | None:
        ...
