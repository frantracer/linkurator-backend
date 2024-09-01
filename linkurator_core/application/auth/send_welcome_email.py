from uuid import UUID

from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.domain.users.user_repository import UserRepository


class SendWelcomeEmail:
    def __init__(self,
                 user_repository: UserRepository,
                 email_sender: EmailSender,
                 base_url: str
                 ) -> None:
        self.user_repository = user_repository
        self.email_sender = email_sender
        self.base_url = base_url

    async def handle(self, user_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            return

        subject = "Linkurator te da la bienvenida"
        message_text = f"¡Hola {user.first_name}!\n\nTe damos la bienvenida a Linkurator: {self.base_url}"
        email = user.email

        await self.email_sender.send_email(email, subject, message_text)
