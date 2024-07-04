import json
import pathlib


class GoogleClientSecrets:
    client_id: str
    client_secret: str
    api_keys: list[str]
    gmail_refresh_token: str

    def __init__(self, file_path: str = '', api_key_path: str = '', gmail_refresh_token_path: str = '') -> None:
        current_path = pathlib.Path(__file__).parent.absolute()

        if file_path == '':
            file_path = f'{current_path}/../../../secrets/client_secret.json'
        with open(file_path, "r", encoding='UTF-8') as secrets_file:
            secrets = json.loads(secrets_file.read())
        self.client_id = secrets["web"]["client_id"]
        self.client_secret = secrets["web"]["client_secret"]

        if api_key_path == '':
            api_key_path = f'{current_path}/../../../secrets/google_api_key.txt'
        with open(api_key_path, "r", encoding='UTF-8') as api_key_file:
            self.api_keys = [key for key in api_key_file.read().splitlines() if key.strip() != '']

        if gmail_refresh_token_path == '':
            gmail_refresh_token_path = f'{current_path}/../../../secrets/gmail_refresh_token.txt'
        with open(gmail_refresh_token_path, "r", encoding='UTF-8') as gmail_refresh_token_file:
            self.gmail_refresh_token = gmail_refresh_token_file.read().strip()
