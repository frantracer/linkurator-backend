import argparse
from dataclasses import dataclass
from enum import Enum
from urllib.parse import parse_qs, urlparse

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


class Scopes(Enum):
    YOUTUBE = "YOUTUBE"
    GMAIL = "GMAIL"


@dataclass
class Arguments:
    scopes: Scopes


def parse_arguments() -> Arguments:
    parser = argparse.ArgumentParser(description='Generate a Google refresh token')
    parser.add_argument('--scope', choices=[field.value for field in list(Scopes)], default=Scopes.YOUTUBE,
                        help='The scopes to request the refresh token for')

    args = parser.parse_args()
    return Arguments(scopes=Scopes(args.scope))


def main() -> None:
    arguments = parse_arguments()

    google_secrets = GoogleClientSecrets()
    google_account_service = GoogleAccountService(client_id=google_secrets.client_id,
                                                  client_secret=google_secrets.client_secret)
    redirect_uri = "http://localhost:9000/login_auth"

    scopes = ["openid", "profile", "email"]
    if arguments.scopes == Scopes.GMAIL:
        scopes = scopes + ["https://www.googleapis.com/auth/gmail.send"]
    elif arguments.scopes == Scopes.YOUTUBE:
        scopes = scopes + ["https://www.googleapis.com/auth/youtube"]

    auth_url = google_account_service.authorization_url(scopes, redirect_uri)

    print(f'Please visit the following URL to authorize the application:\n {auth_url}')
    print('\nAfter authorization, copy the redirected URL and paste it here:')
    redirect_url_str = input()

    url = urlparse(redirect_url_str)
    code = parse_qs(url.query)["code"][0]
    print(f'\nCode: {code}')

    tokens = google_account_service.validate_code(code, redirect_uri)
    if tokens is not None and tokens.refresh_token is None:
        google_account_service.revoke_credentials(tokens.access_token)

        print(f'\nYour credentials were revoke. Please log in again using the following URL:\n {auth_url}')
        print('\nAfter authorization, copy the redirected URL and paste it here:')
        redirect_url_str = input()

        url = urlparse(redirect_url_str)
        code = parse_qs(url.query)["code"][0]

        tokens = google_account_service.validate_code(code, redirect_uri)

    if tokens is not None and tokens.refresh_token is not None:
        print(f'\nRefresh token: {tokens.refresh_token}')
    else:
        print('\nSomething went wrong. Please try again.')


if __name__ == '__main__':
    main()
