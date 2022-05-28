import json
import pathlib
from urllib.parse import parse_qs, urlparse

from linkurator_core.infrastructure.google.account_service import GoogleAccountService


def main():
    secret_path = f'{pathlib.Path(__file__).parent.absolute()}/../secrets/client_secret.json'
    with open(secret_path, "r", encoding='UTF-8') as secrets_file:
        secrets = json.loads(secrets_file.read())
    client_id = secrets["web"]["client_id"]
    client_secret = secrets["web"]["client_secret"]

    google_account_service = GoogleAccountService(client_id=client_id, client_secret=client_secret)
    redirect_uri = "https://localhost:9000/auth"

    scopes = ["openid", "profile", "email", "https://www.googleapis.com/auth/youtube.readonly"]
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
