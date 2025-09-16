from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.usage import RunUsage


class KeywordOutput(BaseModel):
    keywords: list[str] = Field(
        description="List of keywords and keyword combinations for searching content. "
                    "Each keyword can contain multiple words that must appear together in titles.",
    )


class KeywordGeneratorAgent:
    def __init__(self, google_api_key: str) -> None:
        self.agent = create_keyword_generator_agent(google_api_key)

    async def generate_keywords(self, query: str, usage: RunUsage) -> list[str]:
        result = await self.agent.run(user_prompt=query, usage=usage)
        return result.output.keywords


def create_keyword_generator_agent(api_key: str) -> Agent[None, KeywordOutput]:
    provider = GoogleProvider(api_key=api_key)

    gemini_flash_model = GoogleModel(
        provider=provider,
        model_name="gemini-2.5-flash",
        settings=GoogleModelSettings(
            temperature=0.3,
            google_thinking_config={"thinking_budget": 0},
        ),
    )

    return Agent[None, KeywordOutput](
        gemini_flash_model,
        name="KeywordGeneratorAgent",
        output_type=KeywordOutput,
        system_prompt=(
            "You are a keyword generation system that converts user queries into effective search keywords "
            "for finding videos and podcasts on YouTube and Spotify.\n\n"
            "Your task is to generate a comprehensive list of keywords that would help find relevant content. "
            "Consider the following guidelines:\n\n"
            "- Extract main concepts and topics from the user's query\n"
            "- Generate both specific and broader keyword variations\n"
            "- Include synonyms and related terms\n"
            "- Create multi-word combinations that capture specific topics\n"
            "- Consider both technical and common language terms\n"
            "- Maximum 10 keywords total\n"
            "- Each keyword should be three words maximum\n"
            "- Combinations of one or two words are preferred\n"
            "- Focus on keywords that appears on titles\n"
            "- Avoid overly generic terms\n"
            "- Prioritize substantive nouns, proper nouns, and specific descriptive terms\n"
            "\nExamples:\n"
            "- User query: 'machine learning tutorials for beginners'\n"
            "  Keywords: ['machine learning', 'ML tutorial', 'ML beginner', 'artificial intelligence', 'AI basics', 'deep learning', 'neural networks', 'data science']\n\n"
            "- User query: 'best practices for React development'\n"
            "  Keywords: ['React', 'React best practices', 'React development', 'React tips', 'React tutorial', 'JavaScript', 'frontend', 'web development']\n\n"
            "- User query: 'cooking pasta recipes'\n"
            "  Keywords: ['pasta', 'pasta recipe', 'cooking pasta', 'Italian food', 'spaghetti', 'carbonara', 'pasta sauce', 'cooking tutorial']\n\n"
        ),
    )
