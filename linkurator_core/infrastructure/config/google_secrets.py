import json
from pathlib import Path
from plistlib import InvalidFileException


class GoogleClientSecrets:
    client_id: str
    client_secret: str
    api_keys: list[str]
    email_service_credentials_path: Path

    def __init__(self, file_path: str = '', api_key_path: str = '',
                 email_service_credentials_path: Path | None = None) -> None:
        current_path = Path(__file__).parent.absolute()
        secrets_path = Path(f'{current_path}/../../../secrets')

        if file_path == '':
            file_path = f'{secrets_path}/client_secret.json'
        with open(file_path, "r", encoding='UTF-8') as secrets_file:
            secrets = json.loads(secrets_file.read())
        self.client_id = secrets["web"]["client_id"]
        self.client_secret = secrets["web"]["client_secret"]

        if api_key_path == '':
            api_key_path = f'{secrets_path}/google_api_key.txt'
        with open(api_key_path, "r", encoding='UTF-8') as api_key_file:
            self.api_keys = [key for key in api_key_file.read().splitlines() if key.strip() != '']

        if email_service_credentials_path is None:
            self.email_service_credentials_path = Path(f'{secrets_path}/domain_service_credentials.json')
        if not self.email_service_credentials_path.exists():
            raise InvalidFileException(f"File {email_service_credentials_path} does not exist")
