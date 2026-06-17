from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage


class KeywordOutput(BaseModel):
    keywords: list[str] = Field(
        description="List of keywords and keyword combinations for searching content. "
                    "Each keyword can contain multiple words that must appear together in titles.",
    )


class KeywordGeneratorAgent:
    def __init__(self, model: Model) -> None:
        self.agent = create_keyword_generator_agent(model)

    async def generate_keywords(self, query: str, usage: RunUsage) -> list[str]:
        result = await self.agent.run(user_prompt=query, usage=usage)
        return result.output.keywords


def create_keyword_generator_agent(model: Model) -> Agent[None, KeywordOutput]:
    return Agent[None, KeywordOutput](
        model,
        name="KeywordGeneratorAgent",
        output_type=KeywordOutput,
        model_settings=ModelSettings(
            temperature=0.3,
        ),
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
            "- Always include the most important nouns from the query as standalone single-word keywords\n"
            "- Focus on keywords that appears on titles\n"
            "- Avoid overly generic terms\n"
            "- Prioritize substantive nouns, proper nouns, and specific descriptive terms\n"
            "- Preserve the language of the user's query (do not translate keywords)\n"
            "\nExamples:\n"
            "- User query: 'machine learning tutorials for beginners'\n"
            "  Keywords: ['machine learning', 'ML tutorial', 'ML beginner', 'artificial intelligence', 'AI basics', 'deep learning', 'neural networks', 'data science']\n\n"
            "- User query: 'best practices for React development'\n"
            "  Keywords: ['React', 'React best practices', 'React development', 'React tips', 'React tutorial', 'JavaScript', 'frontend', 'web development']\n\n"
            "- User query: 'cooking pasta recipes'\n"
            "  Keywords: ['pasta', 'pasta recipe', 'cooking pasta', 'Italian food', 'spaghetti', 'carbonara', 'pasta sauce', 'cooking tutorial']\n\n"
        ),
    )
