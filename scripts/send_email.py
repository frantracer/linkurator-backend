import argparse
import asyncio
import logging
from dataclasses import dataclass
from uuid import uuid4

from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.google.account_service import GoogleDomainAccountService
from linkurator_core.infrastructure.google.gmail_email_sender import GmailEmailSender

logging.basicConfig(level=logging.INFO)


@dataclass
class InputArguments:
    email: str
    subject: str
    message_text: str


def parse_arguments() -> InputArguments:
    parser = argparse.ArgumentParser(description="Send an email using the Gmail API")
    parser.add_argument("--email", required=True,
                        help="The email address of the recipient")
    parser.add_argument("--subject", default="Linkurator test email",
                        help="The subject of the email")
    parser.add_argument("--message_text", default="Email sent with Gmail API",
                        help="The body of the email")
    parser.add_argument("--html-path", default="",
                        help="Html path to be sent")

    args = parser.parse_args()

    body = args.message_text
    if args.html_path != "":
        with open(args.html_path, encoding="utf-8") as fd:
            body = fd.read()

    return InputArguments(email=args.email, subject=args.subject, message_text=body)


async def main() -> None:
    input_arguments = parse_arguments()

    user_email = input_arguments.email
    subject = input_arguments.subject
    message_text = input_arguments.message_text + f"\n{uuid4()}"

    settings = ApplicationSettings.from_file()
    google_client_secrets = settings.google
    env_settings = settings.env
    google_account_service = GoogleDomainAccountService(
        email=env_settings.GOOGLE_SERVICE_ACCOUNT_EMAIL,
        service_credentials_path=google_client_secrets.email_service_credentials_path)
    email_sender = GmailEmailSender(account_service=google_account_service)

    result = await email_sender.send_email(user_email, subject, message_text)
    if result:
        logging.info("Email sent to successfully %s", user_email)
    else:
        logging.error("Failed to send email")


if __name__ == "__main__":
    asyncio.run(main())
