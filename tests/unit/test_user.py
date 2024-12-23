from datetime import timedelta
from uuid import UUID

import pytest

from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.user import User, Username


def test_user_can_follow_and_unfollow_curator() -> None:
    user = mock_user()

    curator_id = UUID('7660c244-fc8b-49c6-8bdc-97d6b4e05af1')
    user.follow_curator(curator_id=curator_id)
    assert user.curators == {curator_id}

    user.unfollow_curator(curator_id=curator_id)
    assert user.curators == set()


def test_user_can_follow_curator_twice() -> None:
    user = mock_user()

    curator_id = UUID('efa69101-9502-4496-a105-7128a3ccdeba')
    user.follow_curator(curator_id=curator_id)
    user.follow_curator(curator_id=curator_id)

    assert user.curators == {curator_id}


def test_user_can_unfollow_curator_twice() -> None:
    user = mock_user()

    curator_id = UUID('757faf19-ef3c-4e98-bde2-920f98c6198d')
    user.unfollow_curator(curator_id=curator_id)
    user.unfollow_curator(curator_id=curator_id)

    assert user.curators == set()


def test_create_password_and_validate_it() -> None:
    user = mock_user()

    password = "password"
    user.set_password(password=password)

    assert user.validate_password(password=password)
    assert not user.validate_password(password="wrong_password")


def test_cannot_create_invalid_username() -> None:
    with pytest.raises(ValueError):
        Username("a a")


def test_valid_username_characters() -> None:
    username = Username("az09.!#$%&'*+/=?^_`{|}~-")
    assert str(username) == "az09.!#$%&'*+/=?^_`{|}~-"


def test_unfollow_and_follow_youtube_subscription() -> None:
    sub_id = UUID('82ef95e0-c9d5-4a9f-8130-39502fade902')
    user = mock_user()
    user.set_youtube_subscriptions({sub_id})
    user.unfollow_subscription(sub_id)
    assert user.get_subscriptions() == set()

    user.follow_subscription(sub_id)
    assert user.get_subscriptions() == {sub_id}


def test_transform_username() -> None:
    assert str(Username.transform("Test User")) == "test_user"

    assert str(Username.transform("Test User 1")) == "test_user_1"


def test_user_is_active() -> None:
    user = mock_user()

    assert user.is_active()


def test_user_is_not_active() -> None:
    user = mock_user()
    user.last_login_at = User.time_since_last_active() - timedelta(minutes=1)

    assert not user.is_active()
