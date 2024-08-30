from uuid import UUID

from linkurator_core.domain.common.mock_factory import mock_user


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
