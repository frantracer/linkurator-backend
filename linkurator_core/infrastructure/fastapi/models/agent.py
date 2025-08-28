from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    query: str = Field(
        description="The query to send to the AI agent",
        min_length=1,
    )
