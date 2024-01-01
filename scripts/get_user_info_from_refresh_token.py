import argparse

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


def main() -> None:
    parser = argparse.ArgumentParser(description='Get google account user information')
    parser.add_argument('--refresh-token', type=str, required=True,
                        help='Refresh token that will be used to get the Access token')
    args = parser.parse_args()

    refresh_token = args.refresh_token

    google_secrets = GoogleClientSecrets()
    google_account_service = GoogleAccountService(client_id=google_secrets.client_id,
                                                  client_secret=google_secrets.client_secret)

    access_token = google_account_service.generate_access_token_from_refresh_token(refresh_token)

    if access_token is not None:
        user_info = google_account_service.get_user_info(access_token)
        print(user_info)
    else:
        print("Refresh token is not valid")


if __name__ == '__main__':
    main()
