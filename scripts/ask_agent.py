import asyncio
import logging
from uuid import uuid4

import logfire

from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.infrastructure.ai_agents.main_query_agent import MainQueryAgent
from linkurator_core.infrastructure.ai_agents.model import create_agent_model
from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository
from linkurator_core.infrastructure.postgres.chat_repository import PostgresChatRepository
from linkurator_core.infrastructure.postgres.item_repository import PostgresItemRepository
from linkurator_core.infrastructure.postgres.subscription_repository import PostgresSubscriptionRepository
from linkurator_core.infrastructure.postgres.topic_repository import PostgresTopicRepository


async def main() -> None:
    settings = ApplicationSettings.from_file()
    db_settings = settings.postgres

    logfire.configure(token=settings.logging.logfire.token, scrubbing=False)

    # Repositories
    user_repository = InMemoryUserRepository()
    subscription_repository = PostgresSubscriptionRepository(
        ip=db_settings.ip_address, port=db_settings.port, db_name=db_settings.database,
        username=db_settings.user, password=db_settings.password,
    )
    item_repository = PostgresItemRepository(
        ip=db_settings.ip_address, port=db_settings.port, db_name=db_settings.database,
        username=db_settings.user, password=db_settings.password,
    )
    topic_repository = PostgresTopicRepository(
        ip=db_settings.ip_address, port=db_settings.port, db_name=db_settings.database,
        username=db_settings.user, password=db_settings.password,
    )
    chat_repository = PostgresChatRepository(
        ip=db_settings.ip_address, port=db_settings.port, db_name=db_settings.database,
        username=db_settings.user, password=db_settings.password,
    )

    user = mock_user()
    await user_repository.add(user)

    agent = MainQueryAgent(
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        item_repository=item_repository,
        topic_repository=topic_repository,
        chat_repository=chat_repository,
        base_url="http://localhost:8000",
        model=create_agent_model(
            openai_api_key=settings.openai.api_key,
            mistral_api_key=settings.mistral_ai.api_key,
        ),
    )

    result = await agent.query(
        user_id=user.uuid,
        query="Group my subscriptions into topics",
        chat_id=uuid4(),
    )
    logging.info(result.message)

    result = await agent.query(
        user_id=user.uuid,
        query="Recommend some content for me in Spanish or English",
        chat_id=uuid4(),
    )
    logging.info(result.message)


if __name__ == "__main__":
    asyncio.run(main())
