from typing import Callable
from urllib.parse import urljoin
from uuid import UUID, uuid4

from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.domain.users.password_change_request_repository import PasswordChangeRequestRepository
from linkurator_core.domain.users.user_repository import UserRepository

PASSWORD_CHANGE_REQUEST_EXPIRATION_TIME = 60 * 10  # 10 minutes


class RequestPasswordChange:
    def __init__(self,
                 user_repository: UserRepository,
                 password_change_request_repository: PasswordChangeRequestRepository,
                 email_sender: EmailSender,
                 base_url: str,
                 uuid_generator: Callable[[], UUID] = uuid4
                 ) -> None:
        self.user_repository = user_repository
        self.password_change_request_repository = password_change_request_repository
        self.email_sender = email_sender
        self.base_url = base_url
        self.uuid_generator = uuid_generator

    async def handle(self, email: str) -> None:
        user = await self.user_repository.get_by_email(email)
        if user is None:
            return

        request = PasswordChangeRequest.new(user_id=user.uuid,
                                            seconds_to_expire=PASSWORD_CHANGE_REQUEST_EXPIRATION_TIME,
                                            uuid_generator=self.uuid_generator)
        await self.password_change_request_repository.add_request(request)

        link = urljoin(self.base_url + "/", str(request.uuid))
        email = user.email
        subject = "Solicitud de cambio de contraseña"
        message = f"Para cambiar tu contraseña, haz clic en el siguiente enlace: {link}"
        await self.email_sender.send_email(email, subject, message)
