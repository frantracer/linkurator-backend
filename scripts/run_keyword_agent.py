import argparse
import asyncio
import logging

from pydantic_ai.usage import RunUsage

from linkurator_core.infrastructure.ai_agents.keyword_generator_agent import KeywordGeneratorAgent
from linkurator_core.infrastructure.config.settings import ApplicationSettings


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the keyword generator agent")
    parser.add_argument("query", help="Query to generate keywords for")
    args = parser.parse_args()

    settings = ApplicationSettings.from_file()

    agent = KeywordGeneratorAgent(google_api_key=settings.google_ai.gemini_api_key)
    usage = RunUsage()

    logging.info(f"Generating keywords for query: '{args.query}'")
    logging.info("=" * 50)

    keywords = await agent.generate_keywords(args.query, usage)

    logging.info(f"Generated {len(keywords)} keywords:")
    for i, keyword in enumerate(keywords, 1):
        logging.info(f"{i:2d}. {keyword}")

    logging.info("=" * 50)
    logging.info(f"Usage: {usage}")


if __name__ == "__main__":
    asyncio.run(main())
