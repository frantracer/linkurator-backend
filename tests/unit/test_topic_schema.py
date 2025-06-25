from uuid import UUID

from linkurator_core.domain.common.mock_factory import mock_topic, mock_user
from linkurator_core.infrastructure.fastapi.models.topic import TopicSchema


def test_topic_schema_from_domain_topic_with_favorite() -> None:
    topic_id = UUID("615035e7-7d11-41e1-ac29-66ae824e7530")
    curator_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")
    user_id = UUID("7660c244-fc8b-49c6-8bdc-97d6b4e05af1")

    curator = mock_user(uuid=curator_id)
    user = mock_user(uuid=user_id)
    topic = mock_topic(uuid=topic_id, user_uuid=curator_id)

    # User has favorited this topic
    user.favorite_topic(topic_id)

    schema = TopicSchema.from_domain_topic(topic, curator, user)

    assert schema.uuid == topic_id
    assert schema.name == topic.name
    assert schema.user_id == curator_id
    assert schema.subscriptions_ids == topic.subscriptions_ids
    assert schema.is_owner is False
    assert schema.followed is False
    assert schema.is_favorite is True
    assert schema.created_at == topic.created_at
    assert schema.curator.id == curator_id


def test_topic_schema_from_domain_topic_without_favorite() -> None:
    topic_id = UUID("615035e7-7d11-41e1-ac29-66ae824e7530")
    curator_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")
    user_id = UUID("7660c244-fc8b-49c6-8bdc-97d6b4e05af1")

    curator = mock_user(uuid=curator_id)
    user = mock_user(uuid=user_id)
    topic = mock_topic(uuid=topic_id, user_uuid=curator_id)

    schema = TopicSchema.from_domain_topic(topic, curator, user)

    assert schema.uuid == topic_id
    assert schema.is_favorite is False


def test_topic_schema_from_domain_topic_user_owns_topic_and_favorites_it() -> None:
    topic_id = UUID("615035e7-7d11-41e1-ac29-66ae824e7530")
    user_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    user = mock_user(uuid=user_id)
    topic = mock_topic(uuid=topic_id, user_uuid=user_id)

    # User owns and favorites their own topic
    user.favorite_topic(topic_id)

    schema = TopicSchema.from_domain_topic(topic, user, user)

    assert schema.uuid == topic_id
    assert schema.is_owner is True
    assert schema.is_favorite is True


def test_topic_schema_from_domain_topic_no_user() -> None:
    topic_id = UUID("615035e7-7d11-41e1-ac29-66ae824e7530")
    curator_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    curator = mock_user(uuid=curator_id)
    topic = mock_topic(uuid=topic_id, user_uuid=curator_id)

    schema = TopicSchema.from_domain_topic(topic, curator, None)

    assert schema.uuid == topic_id
    assert schema.is_owner is False
    assert schema.followed is False
    assert schema.is_favorite is False


def test_topic_schema_from_domain_topic_user_follows_and_favorites() -> None:
    topic_id = UUID("615035e7-7d11-41e1-ac29-66ae824e7530")
    curator_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")
    user_id = UUID("7660c244-fc8b-49c6-8bdc-97d6b4e05af1")

    curator = mock_user(uuid=curator_id)
    user = mock_user(uuid=user_id)
    topic = mock_topic(uuid=topic_id, user_uuid=curator_id)

    # User both follows and favorites the topic
    user.follow_topic(topic_id)
    user.favorite_topic(topic_id)

    schema = TopicSchema.from_domain_topic(topic, curator, user)

    assert schema.uuid == topic_id
    assert schema.is_owner is False
    assert schema.followed is True
    assert schema.is_favorite is True
