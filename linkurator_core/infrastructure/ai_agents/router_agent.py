from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage


class RouterOutput(BaseModel):
    agent_type: Literal["recommendations", "topic_manager"] = Field(
        description="The type of agent that should handle this query",
    )
    reasoning: str = Field(
        description="Explanation of why this agent type was chosen",
    )


class RouterAgent:
    def __init__(self, mistral_api_key: str) -> None:
        self.agent = create_router_agent(mistral_api_key)

    async def query(self, query: str, usage: RunUsage) -> RouterOutput:
        result = await self.agent.run(user_prompt=query, usage=usage)
        return result.output


def create_router_agent(api_key: str) -> Agent[None, RouterOutput]:
    provider = MistralProvider(api_key=api_key)

    mistral_model = MistralModel(
        model_name="mistral-small-latest",
        provider=provider,
        settings=ModelSettings(
            temperature=0.1,
        ),
    )

    return Agent[None, RouterOutput](
        mistral_model,
        name="RouterAgent",
        output_type=RouterOutput,
        system_prompt=(
            "You are a router agent that determines which specialized agent should handle a user query. "
            "Your job is to analyze the query and route it to the appropriate agent:\n\n"
            "- 'recommendations': For queries asking for content recommendations, searching for specific videos/podcasts, "
            "finding items by keywords, or general content discovery requests.\n"
            "- 'topic_manager': For queries about creating, managing, organizing topics, or managing subscriptions within topics.\n\n"
            "Always choose 'recommendations' as the default unless the query explicitly mentions topics management."
        ),
    )
