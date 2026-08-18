from __future__ import annotations

from ipaddress import IPv4Address

from linkurator_core.infrastructure.postgres.common import PostgresConnector
from linkurator_core.infrastructure.rss.rss_data_repository import RawDataRecord, RssDataRepository


class PostgresRssDataRepository(RssDataRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def set_raw_data(self, records: list[RawDataRecord]) -> None:
        if len(records) == 0:
            return
        pool = await self._connector.pool()
        await pool.executemany(
            """
            INSERT INTO rss_data (rss_url, item_url, raw_data)
            VALUES (%s, %s, %s)
            ON CONFLICT (rss_url, item_url) DO UPDATE SET raw_data = EXCLUDED.raw_data
            """,
            [(record.rss_url, record.item_url, record.raw_data) for record in records],
        )

    async def get_raw_data(self, rss_url: str, item_url: str) -> str | None:
        pool = await self._connector.pool()
        return await pool.fetchval(
            "SELECT raw_data FROM rss_data WHERE rss_url = %s AND item_url = %s", rss_url, item_url,
        )
