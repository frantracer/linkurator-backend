from abc import ABC, abstractmethod
from dataclasses import dataclass

from linkurator_core.domain.subscriptions.subscription import Subscription


@dataclass
class SummarizeAgentResult:
    summary: str


class SummarizeAgentService(ABC):
    @abstractmethod
    async def summarize(self, subscription: Subscription) -> SummarizeAgentResult:
        pass
