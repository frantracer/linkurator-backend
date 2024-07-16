from ipaddress import IPv4Address
from uuid import UUID

import pytest

from linkurator_core.infrastructure.mongodb.followed_topics_repository import MongoDBFollowedTopicsRepository


@pytest.fixture(name="followed_topics_repo", scope="session")
def fixture_followed_topics_repo(db_name: str) -> MongoDBFollowedTopicsRepository:
    return MongoDBFollowedTopicsRepository(
        IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio
async def test_follow_topic(followed_topics_repo: MongoDBFollowedTopicsRepository) -> None:
    user_uuid = UUID('1afbea6e-0012-422d-bc12-29f18abcb7b4')
    topic_uuid = UUID('0643b520-73bf-4f58-bbd6-0dd2be867b27')
    await followed_topics_repo.follow_topic(user_uuid, topic_uuid)
    followed_topics = await followed_topics_repo.get_followed_topics(user_uuid)
    assert len(followed_topics) == 1
    assert followed_topics[0].user_uuid == user_uuid
    assert followed_topics[0].topic_uuid == topic_uuid
    assert followed_topics[0].created_at is not None


@pytest.mark.asyncio
async def test_unfollow_topic(followed_topics_repo: MongoDBFollowedTopicsRepository) -> None:
    user_uuid = UUID('8109e7e2-12ed-4022-8fb3-481d20d39b11')
    topic_uuid = UUID('c4166b07-3d48-421e-928f-630ec2893e2c')
    await followed_topics_repo.follow_topic(user_uuid, topic_uuid)
    followed_topics = await followed_topics_repo.get_followed_topics(user_uuid)
    assert len(followed_topics) == 1
    await followed_topics_repo.unfollow_topic(user_uuid, topic_uuid)
    followed_topics = await followed_topics_repo.get_followed_topics(user_uuid)
    assert len(followed_topics) == 0


@pytest.mark.asyncio
async def test_unfollow_a_non_followed_topic_does_not_return_an_error(
        followed_topics_repo: MongoDBFollowedTopicsRepository) -> None:
    user_uuid = UUID('b9a54612-9ee4-4e4c-a22c-a7445c330921')
    topic_uuid = UUID('a3a41be0-63ab-4447-9054-1bb78a3e39cc')
    await followed_topics_repo.unfollow_topic(user_uuid, topic_uuid)
    followed_topics = await followed_topics_repo.get_followed_topics(user_uuid)
    assert len(followed_topics) == 0
