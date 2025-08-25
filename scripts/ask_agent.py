import asyncio
import logging
from uuid import UUID

import logfire

from linkurator_core.infrastructure.ai_agents.pydantic_ai_agent import AgentDependencies, create_agent
from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository
from linkurator_core.infrastructure.mongodb.topic_repository import MongoDBTopicRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository


async def main() -> None:
    settings = ApplicationSettings.from_file()
    db_settings = settings.mongodb

    logfire.configure(token=settings.log.logfire_token, scrubbing=False)

    # Repositories
    user_repository = MongoDBUserRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )
    subscription_repository = MongoDBSubscriptionRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )
    item_repository = MongoDBItemRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )
    topic_repository = MongoDBTopicRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )

    deps = AgentDependencies(
        user_uuid=UUID("97fda3e1-8f3d-4068-a6a6-5583c1d9e220"),
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        item_repository=item_repository,
        topic_repository=topic_repository,
        previous_chat=None,
    )
    support_agent = create_agent(settings.google_ai.api_key)

    result = await support_agent.run(
        "Group my subscriptions into topics",
        deps=deps,
    )
    logging.info(result.output)

    result = await support_agent.run(
        "Recommend some content for me in Spanish or English",
        deps=deps,
    )
    logging.info(result.output)


if __name__ == "__main__":
    asyncio.run(main())
