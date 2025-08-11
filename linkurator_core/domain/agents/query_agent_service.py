from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass
class AgentQueryResult:
    message: str
    items: list[UUID]
    topics: list[UUID]
    subscriptions: list[UUID]


class QueryAgentService(ABC):
    @abstractmethod
    async def query(self, user_id: UUID, query: str) -> AgentQueryResult:
        pass