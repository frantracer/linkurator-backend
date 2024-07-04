import argparse
import asyncio
from dataclasses import dataclass
from uuid import uuid4

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.gmail_email_sender import GmailEmailSender


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

    args = parser.parse_args()
    return InputArguments(email=args.email, subject=args.subject, message_text=args.message_text)


async def main() -> None:
    input_arguments = parse_arguments()

    user_email = input_arguments.email
    subject = input_arguments.subject
    message_text = input_arguments.message_text + f"\n{uuid4()}"

    google_client_secrets = GoogleClientSecrets()
    google_account_service = GoogleAccountService(
        client_id=google_client_secrets.client_id,
        client_secret=google_client_secrets.client_secret)
    email_sender = GmailEmailSender(refresh_token=google_client_secrets.gmail_refresh_token,
                                    account_service=google_account_service)

    result = await email_sender.send_email(user_email, subject, message_text)
    if result:
        print(f"Email sent to {user_email} successfully")
    else:
        print("Failed to send email")


if __name__ == "__main__":
    asyncio.run(main())
