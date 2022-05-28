import json
import pathlib


class GoogleClientSecrets:
    client_id: str
    client_secret: str

    def __init__(self, file_path: str = ''):
        if file_path == '':
            file_path = f'{pathlib.Path(__file__).parent.absolute()}/../../../secrets/client_secret.json'
        with open(file_path, "r", encoding='UTF-8') as secrets_file:
            secrets = json.loads(secrets_file.read())
        self.client_id = secrets["web"]["client_id"]
        self.client_secret = secrets["web"]["client_secret"]
