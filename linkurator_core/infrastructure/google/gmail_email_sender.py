import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiohttp

from linkurator_core.infrastructure.google.account_service import GoogleAccountService


class GmailEmailSender:
    def __init__(self, refresh_token: str, account_service: GoogleAccountService) -> None:
        self.refresh_token = refresh_token
        self.account_service = account_service
        self.access_token: str | None = None

    async def send_email(self, user_email: str, subject: str, message_text: str) -> bool:
        """
        Send an email using the Gmail API and a refresh token.
        :param user_email: The email address of the recipient.
        :param subject: The subject of the email.
        :param message_text: The body of the email.
        :return: True if the email was sent successfully, False otherwise.
        """
        if self.access_token is None:
            self.access_token = self.account_service.generate_access_token_from_refresh_token(self.refresh_token)

        if self.access_token is None:
            logging.error("Failed to generate access token for the Gmail API")
            return False

        message = MIMEMultipart()
        message['to'] = user_email
        message['subject'] = subject
        message.attach(MIMEText(message_text))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        send_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        payload = {'raw': raw_message}

        async with aiohttp.ClientSession() as session:
            async with session.post(send_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    return True
        return False
