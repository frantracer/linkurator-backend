import pytest
from pydantic import AnyUrl

from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.registration_request import RegistrationRequest


@pytest.mark.asyncio
async def test_create_registration_request_with_invalid_domain_raises_an_error() -> None:
    with pytest.raises(ValueError):
        RegistrationRequest.new(
            user=mock_user(),
            seconds_to_expire=1,
            validation_base_url=AnyUrl("https://invalid.com"))
