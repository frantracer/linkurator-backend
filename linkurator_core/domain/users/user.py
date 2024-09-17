from __future__ import annotations

import hashlib
from copy import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Callable
from uuid import UUID, uuid4

from pydantic import AnyUrl, Field, RootModel


def default_salt_generator() -> str:
    return uuid4().hex


def default_hash_function(text_input: str) -> str:
    return hashlib.sha512(text_input.encode('utf-8')).hexdigest()


class Username(RootModel[str]):
    root: str = Field(min_length=3, max_length=50, pattern=r"^[a-z0-9_-]+$")

    def __str__(self) -> str:
        return str(self.root)


@dataclass
class HashedPassword:
    hashed_pass_plus_salt: str
    salt: str

    @classmethod
    def new(cls,
            input_hash: str,
            salt_generator: Callable[[], str] = default_salt_generator,
            hash_function: Callable[[str], str] = default_hash_function
            ) -> HashedPassword:
        salt = salt_generator()
        pass_to_hash = input_hash + salt
        return cls(
            hashed_pass_plus_salt=hash_function(pass_to_hash),
            salt=salt
        )

    def validate(self,
                 input_hash: str,
                 hash_function: Callable[[str], str] = default_hash_function
                 ) -> bool:
        return self.hashed_pass_plus_salt == hash_function(input_hash + self.salt)


@dataclass
class User:
    uuid: UUID
    first_name: str
    last_name: str
    username: Username
    email: str
    avatar_url: AnyUrl
    locale: str
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime
    last_login_at: datetime
    google_refresh_token: Optional[str]
    password_hash: Optional[HashedPassword]
    _youtube_subscriptions_uuids: set[UUID]
    _unfollowed_youtube_subscriptions_uuids: set[UUID]
    _subscription_uuids: set[UUID]
    _followed_topics: set[UUID]
    is_admin: bool
    curators: set[UUID]

    @classmethod
    def new(cls,
            uuid: UUID,
            first_name: str,
            last_name: str,
            username: Username,
            email: str,
            avatar_url: AnyUrl,
            locale: str,
            google_refresh_token: Optional[str],
            subscription_uuids: Optional[set[UUID]] = None,
            is_admin: bool = False,
            curators: Optional[set[UUID]] = None,
            followed_topics: Optional[set[UUID]] = None
            ) -> User:
        now = datetime.now(timezone.utc)
        return cls(
            uuid=uuid,
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            avatar_url=avatar_url,
            locale=locale,
            created_at=now,
            updated_at=now,
            scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
            last_login_at=now,
            google_refresh_token=google_refresh_token,
            _youtube_subscriptions_uuids=set(),
            _subscription_uuids=set() if subscription_uuids is None else subscription_uuids,
            _unfollowed_youtube_subscriptions_uuids=set(),
            _followed_topics=set() if followed_topics is None else followed_topics,
            is_admin=is_admin,
            curators=set() if curators is None else curators,
            password_hash=None
        )

    def follow_topic(self, topic_id: UUID) -> None:
        self._followed_topics.add(topic_id)

    def unfollow_topic(self, topic_id: UUID) -> None:
        if topic_id in self._followed_topics:
            self._followed_topics.remove(topic_id)

    def get_followed_topics(self) -> set[UUID]:
        return self._followed_topics

    def follow_curator(self, curator_id: UUID) -> None:
        self.curators.add(curator_id)

    def unfollow_curator(self, curator_id: UUID) -> None:
        if curator_id in self.curators:
            self.curators.remove(curator_id)

    def follow_subscription(self, subscription_id: UUID) -> None:
        self._subscription_uuids.add(subscription_id)
        if subscription_id in self._unfollowed_youtube_subscriptions_uuids:
            self._unfollowed_youtube_subscriptions_uuids.remove(subscription_id)

    def unfollow_subscription(self, subscription_id: UUID) -> None:
        if subscription_id in self._subscription_uuids:
            self._subscription_uuids.remove(subscription_id)
        if subscription_id in self._youtube_subscriptions_uuids:
            self._unfollowed_youtube_subscriptions_uuids.add(subscription_id)

    def set_youtube_subscriptions(self, subscription_ids: set[UUID]) -> None:
        self._youtube_subscriptions_uuids = subscription_ids

    def get_youtube_subscriptions(self) -> set[UUID]:
        return copy(self._youtube_subscriptions_uuids)

    def get_youtube_unfollowed_subscriptions(self) -> set[UUID]:
        return copy(self._unfollowed_youtube_subscriptions_uuids)

    def get_subscriptions(self, include_youtube: bool = True) -> set[UUID]:
        uuids = copy(self._subscription_uuids)
        if include_youtube:
            uuids = (uuids
                     .union(self._youtube_subscriptions_uuids)
                     .difference(self._unfollowed_youtube_subscriptions_uuids))
        return uuids

    def set_password(self, password: str) -> None:
        self.password_hash = HashedPassword.new(password)

    def validate_password(self, password: str) -> bool:
        if self.password_hash is None:
            return False
        return self.password_hash.validate(password)
