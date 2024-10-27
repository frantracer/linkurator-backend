import logging
from pathlib import Path
from uuid import UUID

import jinja2
from pydantic import AnyUrl

from linkurator_core.domain.common.exceptions import NonExistingFileError
from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.domain.users.user_repository import UserRepository

WELCOME_EMAIL_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "bienvenida_linkurator.html"
if not WELCOME_EMAIL_TEMPLATE_PATH.exists():
    raise NonExistingFileError(str(WELCOME_EMAIL_TEMPLATE_PATH))


class SendWelcomeEmail:
    def __init__(self,
                 user_repository: UserRepository,
                 email_sender: EmailSender,
                 base_url: AnyUrl
                 ) -> None:
        self.user_repository = user_repository
        self.email_sender = email_sender
        self.base_url = base_url

    async def handle(self, user_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            return

        environment = jinja2.Environment()
        template = environment.from_string(WELCOME_EMAIL_TEMPLATE_PATH.read_text())
        message_text = template.render(name=user.first_name, web_url=self.base_url)

        subject = "Linkurator te da la bienvenida"
        email = user.email

        await self.email_sender.send_email(email, subject, message_text)

        logging.info("Welcome email sent to %s", email)
