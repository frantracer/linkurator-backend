from ipaddress import IPv4Address
from typing import Any

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient

from linkurator_core.infrastructure.mongodb.common import MongoDBMapping
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.rss.rss_data_repository import RawDataRecord, RssDataRepository

RAW_DATA_COLLECTION_NAME = "rss_data"


class MongoDBRssDataRepository(RssDataRepository):

    db_name: str

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient[MongoDBMapping](
            f"mongodb://{ip!s}:{port}/", username=username, password=password)
        self.db_name = db_name

    async def check_connection(self) -> None:
        if RAW_DATA_COLLECTION_NAME not in await self.client[self.db_name].list_collection_names():
            msg = f"Collection '{RAW_DATA_COLLECTION_NAME}' is not initialized in database '{self.db_name}'"
            raise CollectionIsNotInitialized(msg)

    async def set_raw_data(self, records: list[RawDataRecord]) -> None:
        collection = self._raw_data_collection()
        for record in records:
            await collection.replace_one(
                {"rss_url": record.rss_url, "item_url": record.item_url},
                {
                    "rss_url": record.rss_url,
                    "item_url": record.item_url,
                    "raw_data": record.raw_data,
                },
                upsert=True,
            )

    async def get_raw_data(self, rss_url: str, item_url: str) -> str | None:
        collection = self._raw_data_collection()
        result = await collection.find_one({"rss_url": rss_url, "item_url": item_url})
        if result:
            return result["raw_data"]
        return None

    def _raw_data_collection(self) -> Any:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            name=RAW_DATA_COLLECTION_NAME,
            codec_options=codec_options)
