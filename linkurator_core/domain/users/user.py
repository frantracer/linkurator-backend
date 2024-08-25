from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import AnyUrl


@dataclass
class User:
    uuid: UUID
    first_name: str
    last_name: str
    username: str
    email: str
    avatar_url: AnyUrl
    locale: str
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime
    last_login_at: datetime
    google_refresh_token: Optional[str]
    _youtube_subscriptions_uuids: set[UUID]
    _subscription_uuids: set[UUID]
    is_admin: bool
    curators: set[UUID]

    @classmethod
    def new(cls,
            uuid: UUID,
            first_name: str,
            last_name: str,
            username: str,
            email: str,
            avatar_url: AnyUrl,
            locale: str,
            google_refresh_token: Optional[str],
            subscription_uuids: Optional[set[UUID]] = None,
            is_admin: bool = False,
            curators: Optional[set[UUID]] = None
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
            is_admin=is_admin,
            curators=set() if curators is None else curators
        )

    def follow_curator(self, curator_id: UUID) -> None:
        self.curators.add(curator_id)

    def unfollow_curator(self, curator_id: UUID) -> None:
        if curator_id in self.curators:
            self.curators.remove(curator_id)

    def follow_subscription(self, subscription_id: UUID) -> None:
        self._subscription_uuids.add(subscription_id)

    def unfollow_subscription(self, subscription_id: UUID) -> None:
        if subscription_id in self._subscription_uuids:
            self._subscription_uuids.remove(subscription_id)

    def set_youtube_subscriptions(self, subscription_ids: set[UUID]) -> None:
        self._youtube_subscriptions_uuids = subscription_ids

    def get_youtube_subscriptions(self) -> set[UUID]:
        return copy(self._youtube_subscriptions_uuids)

    def get_subscriptions(self, include_youtube: bool = True) -> set[UUID]:
        uuids = copy(self._subscription_uuids)
        if include_youtube:
            uuids = uuids.union(self._youtube_subscriptions_uuids)
        return uuids
