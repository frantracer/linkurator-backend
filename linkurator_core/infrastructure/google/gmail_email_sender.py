import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiohttp
import backoff

from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.infrastructure.google.account_service import GoogleDomainAccountService


class InvalidAccessTokenError(Exception):
    pass


class GmailEmailSender(EmailSender):
    def __init__(self, account_service: GoogleDomainAccountService) -> None:
        self.account_service = account_service
        self.access_token: str | None = None

    @backoff.on_exception(backoff.expo,
                          InvalidAccessTokenError,
                          max_tries=3,
                          factor=2,
                          raise_on_giveup=False,
                          giveup=lambda e: False)
    async def send_email(self, user_email: str, subject: str, message_text: str) -> bool:
        """
        Send an email using the Gmail API and a refresh token.
        :param user_email: The email address of the recipient.
        :param subject: The subject of the email.
        :param message_text: The body of the email.
        :return: True if the email was sent successfully, False otherwise.
        """
        logging.info("Sending email to %s", user_email)

        if self.access_token is None:
            self.access_token = self.account_service.generate_access_token_from_service_credentials()

        if self.access_token is None:
            raise InvalidAccessTokenError("Failed to generate access token for the Gmail API")

        message = MIMEMultipart()
        message['to'] = user_email
        message['subject'] = subject
        message.attach(MIMEText(message_text, 'html'))

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
                if response.status == 401:
                    self.access_token = None
                    raise InvalidAccessTokenError("Failed to send email: Invalid access token")
        return False
