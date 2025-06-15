from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, ClassVar
from urllib.parse import urljoin
from uuid import UUID, uuid4

from pydantic import AnyUrl


def default_datetime_generator() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class PasswordChangeRequest:
    uuid: UUID
    user_id: UUID
    valid_until: datetime
    validation_base_url: AnyUrl

    valid_domains: ClassVar[list[str]] = []

    @classmethod
    def new(cls,
            user_id: UUID,
            seconds_to_expire: int,
            validation_base_url: AnyUrl,
            now_function: Callable[[], datetime] = default_datetime_generator,
            uuid_generator: Callable[[], UUID] = uuid4,
            ) -> PasswordChangeRequest:
        main_domain = validation_base_url.host
        if main_domain not in cls.valid_domains:
            msg = f"Invalid domain: {main_domain}"
            raise ValueError(msg)

        return cls(
            uuid=uuid_generator(),
            user_id=user_id,
            valid_until=now_function() + timedelta(seconds=seconds_to_expire),
            validation_base_url=validation_base_url,
        )

    def is_expired(self, now_function: Callable[[], datetime] = default_datetime_generator) -> bool:
        return now_function() > self.valid_until

    def get_validation_url(self) -> AnyUrl:
        return AnyUrl(urljoin(str(self.validation_base_url) + "/", str(self.uuid)))
