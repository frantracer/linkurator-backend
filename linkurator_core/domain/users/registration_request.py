from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Callable, ClassVar
from urllib.parse import urljoin
from uuid import UUID, uuid4

from pydantic import AnyUrl

from linkurator_core.domain.users.user import User


def default_now_function() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class RegistrationRequest:
    uuid: UUID
    user: User
    valid_until: datetime
    validation_base_url: AnyUrl

    valid_domains: ClassVar[list[str]] = []

    @classmethod
    def new(cls,
            user: User,
            seconds_to_expire: int,
            validation_base_url: AnyUrl,
            uuid_generator: Callable[[], UUID] = uuid4,
            now_function: Callable[[], datetime] = default_now_function
            ) -> RegistrationRequest:
        main_domain = validation_base_url.host
        if main_domain not in cls.valid_domains:
            raise ValueError(f"Invalid domain: {main_domain}")

        return cls(
            uuid=uuid_generator(),
            user=user,
            valid_until=now_function() + timedelta(seconds=seconds_to_expire),
            validation_base_url=validation_base_url
        )

    def is_valid(self, now_function: Callable[[], datetime] = default_now_function) -> bool:
        return now_function() < self.valid_until

    def get_validation_url(self) -> AnyUrl:
        return AnyUrl(urljoin(str(self.validation_base_url) + "/", str(self.uuid)))
