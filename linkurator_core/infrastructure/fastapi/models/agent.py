from pydantic import BaseModel, Field

from linkurator_core.domain.agents.query_agent_service import AgentQueryResult
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.topics.topic import Topic


class AgentQueryRequest(BaseModel):
    query: str = Field(
        description="The query to send to the AI agent",
        min_length=1,
    )


class AgentQueryResponse(BaseModel):
    message: str = Field(
        description="The response message from the AI agent",
    )
    items: list[Item] = Field(
        description="List of content item UUIDs referenced by the AI agent",
        default_factory=list,
    )
    topics: list[Topic] = Field(
        description="List of topic UUIDs referenced by the AI agent",
        default_factory=list,
    )
    subscriptions: list[Subscription] = Field(
        description="List of subscription UUIDs referenced by the AI agent",
        default_factory=list,
    )
    topics_were_created: bool = Field(
        description="Whether new topics were created during the query",
    )

    @classmethod
    def from_domain(cls, result: AgentQueryResult) -> "AgentQueryResponse":
        return cls(
            message=result.message,
            items=result.items,
            topics=result.topics,
            subscriptions=result.subscriptions,
            topics_were_created=result.topics_were_created,
        )
