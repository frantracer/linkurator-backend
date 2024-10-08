from uuid import uuid4

import pytest
from pydantic import AnyUrl

from linkurator_core.domain.users.password_change_request import PasswordChangeRequest


@pytest.mark.asyncio
async def test_create_password_change_request_with_invalid_domain_raises_an_error() -> None:
    with pytest.raises(ValueError):
        PasswordChangeRequest.new(
            user_id=uuid4(),
            seconds_to_expire=1,
            validation_base_url=AnyUrl("https://invalid.com"))
