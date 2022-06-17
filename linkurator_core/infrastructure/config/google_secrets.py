import json
import pathlib


class GoogleClientSecrets:
    client_id: str
    client_secret: str
    api_key: str

    def __init__(self, file_path: str = '', api_key_path: str = ''):
        if file_path == '':
            file_path = f'{pathlib.Path(__file__).parent.absolute()}/../../../secrets/client_secret.json'
        with open(file_path, "r", encoding='UTF-8') as secrets_file:
            secrets = json.loads(secrets_file.read())
        self.client_id = secrets["web"]["client_id"]
        self.client_secret = secrets["web"]["client_secret"]

        if api_key_path == '':
            api_key_path = f'{pathlib.Path(__file__).parent.absolute()}/../../../secrets/google_api_key.txt'
        with open(api_key_path, "r", encoding='UTF-8') as api_key_file:
            self.api_key = api_key_file.read()
