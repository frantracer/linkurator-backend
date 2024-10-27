import logging
from pathlib import Path
from uuid import UUID

import jinja2

from linkurator_core.domain.common.exceptions import NonExistingFileError
from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository

VALIDATION_HTML_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "validacion_linkurator.html"
if not VALIDATION_HTML_TEMPLATE_PATH.exists():
    raise NonExistingFileError(str(VALIDATION_HTML_TEMPLATE_PATH))


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

        environment = jinja2.Environment()
        template = environment.from_string(VALIDATION_HTML_TEMPLATE_PATH.read_text())
        message_text = template.render(name=request.user.first_name, validation_url=request.get_validation_url())

        subject = "Valida tu email para acceder a Linkurator"
        email = request.user.email

        await self.email_sender.send_email(user_email=email, subject=subject, message_text=message_text)

        logging.info("Validation email sent to %s", email)
