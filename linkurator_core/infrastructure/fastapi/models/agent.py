from uuid import UUID

from pydantic import BaseModel, Field

from linkurator_core.domain.agents.query_agent_service import AgentQueryResult


class AgentQueryRequest(BaseModel):
    query: str = Field(
        description="The query to send to the AI agent",
        min_length=1,
    )


class AgentQueryResponse(BaseModel):
    message: str = Field(
        description="The response message from the AI agent",
    )
    items: list[UUID] = Field(
        description="List of content item UUIDs referenced by the AI agent",
        default_factory=list,
    )
    topics: list[UUID] = Field(
        description="List of topic UUIDs referenced by the AI agent",
        default_factory=list,
    )
    subscriptions: list[UUID] = Field(
        description="List of subscription UUIDs referenced by the AI agent",
        default_factory=list,
    )

    @classmethod
    def from_domain(cls, result: AgentQueryResult) -> "AgentQueryResponse":
        return cls(
            message=result.message,
            items=result.items,
            topics=result.topics,
            subscriptions=result.subscriptions,
        )
