from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.topics.topic import Topic


@dataclass
class AgentQueryResult:
    message: str
    items: list[Item]
    topics: list[Topic]
    subscriptions: list[Subscription]
    topics_were_created: bool


class QueryAgentService(ABC):
    @abstractmethod
    async def query(self, user_id: UUID, query: str, chat_id: UUID) -> AgentQueryResult:
        pass
