from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider

OPENAI_MODEL_NAME = "gpt-5.4-nano"
MISTRAL_MODEL_NAME = "mistral-small-latest"


def create_agent_model(
        openai_api_key: str | None = None,
        mistral_api_key: str | None = None,
) -> Model:
    """
    Create the model used by the AI agents from the available API keys.

    Both API keys are optional. OpenAI is preferred over Mistral. When both keys are provided,
    OpenAI is used as the primary model and Mistral as a fallback.
    """
    openai_model = OpenAIChatModel(
        OPENAI_MODEL_NAME,
        provider=OpenAIProvider(api_key=openai_api_key),
    ) if openai_api_key else None

    mistral_model = MistralModel(
        MISTRAL_MODEL_NAME,
        provider=MistralProvider(api_key=mistral_api_key),
    ) if mistral_api_key else None

    if openai_model is not None and mistral_model is not None:
        return FallbackModel(openai_model, mistral_model)
    if openai_model is not None:
        return openai_model
    if mistral_model is not None:
        return mistral_model

    msg = "An OpenAI or Mistral API key must be provided to create the agent model."
    raise ValueError(msg)
