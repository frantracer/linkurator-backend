from __future__ import annotations

import abc

from psycopg import AsyncConnection
from psycopg.rows import TupleRow


class BaseMigration(abc.ABC):
    @abc.abstractmethod
    async def upgrade(self, conn: AsyncConnection[TupleRow]) -> None:
        raise NotImplementedError
