from urllib.parse import urljoin
from uuid import UUID

from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository


class SendValidateNewUserEmail:
    def __init__(self,
                 email_sender: EmailSender,
                 registration_request_repository: RegistrationRequestRepository,
                 base_url: str
                 ) -> None:
        self.registration_request_repository = registration_request_repository
        self.email_sender = email_sender
        self.base_url = base_url

    async def handle(self, request_uuid: UUID) -> None:
        request = await self.registration_request_repository.get_request(request_uuid)
        if request is None:
            return

        link = urljoin(self.base_url + "/", str(request_uuid))
        subject = "Valida tu email para acceder a Linkurator"
        message_text = f"Para validar tu email, haz clic en el siguiente enlace: {link}"
        email = request.user.email

        await self.email_sender.send_email(email, subject, message_text)
