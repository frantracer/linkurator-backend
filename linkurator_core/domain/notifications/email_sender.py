import abc


class EmailSender(abc.ABC):
    @abc.abstractmethod
    async def send_email(self, user_email: str, subject: str, message_text: str) -> bool:
        pass
