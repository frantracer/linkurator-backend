import urllib.parse
from enum import Enum
from uuid import uuid4

from pydantic import AnyUrl

from linkurator_core.domain.common.event import UserRegisterRequestSentEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository
from linkurator_core.domain.users.user import User, Username
from linkurator_core.domain.users.user_repository import UserRepository

ONE_DAY_IN_SECONDS = 60 * 60 * 24


class RegistrationError(Enum):
    EMAIL_ALREADY_REGISTERED = "Email already registered"
    USERNAME_ALREADY_REGISTERED = "Username already registered"
    PASSWORD_MUST_BE_HEX_WITH_64_DIGITS = "Invalid password"


def validate_password(password: str) -> bool:
    try:
        int(password, 16)
    except ValueError:
        return False
    return len(password) == 64


def generate_ui_avatar_url(first_name: str, last_name: str) -> AnyUrl:
    encoded_avatar_name = f"{urllib.parse.quote_plus(first_name)}+{urllib.parse.quote_plus(last_name)}"
    return parse_url(f"https://ui-avatars.com/api/?background=06974c&color=fff&name={encoded_avatar_name}")


class RegisterNewUserWithEmail:
    def __init__(self,
                 user_repository: UserRepository,
                 registration_request_repository: RegistrationRequestRepository,
                 event_bus: EventBusService):
        self.user_repository = user_repository
        self.registration_request_repository = registration_request_repository
        self.event_bus = event_bus

    async def handle(
            self,
            email: str,
            password: str,
            first_name: str,
            last_name: str,
            username: Username
    ) -> list[RegistrationError]:
        errors: list[RegistrationError] = []

        user = await self.user_repository.get_by_email(email)
        if user is not None:
            errors.append(RegistrationError.EMAIL_ALREADY_REGISTERED)

        user = await self.user_repository.get_by_username(username)
        if user is not None:
            errors.append(RegistrationError.USERNAME_ALREADY_REGISTERED)

        if not validate_password(password):
            errors.append(RegistrationError.PASSWORD_MUST_BE_HEX_WITH_64_DIGITS)

        if errors:
            return errors

        new_user = User.new(
            uuid=uuid4(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            username=username,
            locale="es",
            avatar_url=generate_ui_avatar_url(first_name, last_name),
            google_refresh_token=None,
        )
        new_user.set_password(password)

        request = RegistrationRequest.new(user=new_user, seconds_to_expire=ONE_DAY_IN_SECONDS)
        await self.registration_request_repository.add_request(request=request)

        event = UserRegisterRequestSentEvent.new(request_uuid=request.uuid)
        await self.event_bus.publish(event=event)

        return []
