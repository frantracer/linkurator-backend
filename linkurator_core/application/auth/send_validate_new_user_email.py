from uuid import UUID

from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository


class SendValidateNewUserEmail:
    def __init__(self,
                 email_sender: EmailSender,
                 registration_request_repository: RegistrationRequestRepository
                 ) -> None:
        self.registration_request_repository = registration_request_repository
        self.email_sender = email_sender

    async def handle(self, request_uuid: UUID) -> None:
        request = await self.registration_request_repository.get_request(request_uuid)
        if request is None:
            return

        validate_url = request.get_validation_url()
        subject = "Valida tu email para acceder a Linkurator"
        message_text = f"Para validar tu email, haz clic en el siguiente enlace: {validate_url}"
        email = request.user.email

        await self.email_sender.send_email(user_email=email, subject=subject, message_text=message_text)
