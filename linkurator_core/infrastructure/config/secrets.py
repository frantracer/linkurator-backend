import json
from pathlib import Path
from plistlib import InvalidFileException

from pydantic import BaseModel


class GoogleClientSecrets(BaseModel):
    client_id: str
    client_secret: str
    api_keys: list[str]
    email_service_credentials_path: Path

    @classmethod
    def from_file(cls, file_path: str = "", api_key_path: str = "",
                 email_service_credentials_path: Path | None = None) -> "GoogleClientSecrets":
        current_path = Path(__file__).parent.absolute()
        secrets_path = Path(f"{current_path}/../../../secrets")

        if file_path == "":
            file_path = f"{secrets_path}/client_secret.json"
        with open(file_path, encoding="UTF-8") as secrets_file:
            secrets = json.loads(secrets_file.read())
        client_id = secrets["web"]["client_id"]
        client_secret = secrets["web"]["client_secret"]

        if api_key_path == "":
            api_key_path = f"{secrets_path}/google_api_key.txt"
        with open(api_key_path, encoding="UTF-8") as api_key_file:
            api_keys = [key for key in api_key_file.read().splitlines() if key.strip() != ""]

        if email_service_credentials_path is None:
            email_service_credentials_path = Path(f"{secrets_path}/domain_service_credentials.json")
        if not email_service_credentials_path.exists():
            msg = f"File {email_service_credentials_path} does not exist"
            raise InvalidFileException(msg)

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            api_keys=api_keys,
            email_service_credentials_path=email_service_credentials_path,
        )


class SpotifyCredentialPair(BaseModel):
    client_id: str
    client_secret: str


class SpotifyClientSecrets(BaseModel):
    credentials: list[SpotifyCredentialPair]

    @classmethod
    def from_file(cls, file_path: str = "") -> "SpotifyClientSecrets":
        """
        Load Spotify credentials from a JSON file.
        :param file_path:
        :return:
        :raises ValueError: If no credentials are found in the file.
        :raises TypeError: If the file format is invalid.
        """
        current_path = Path(__file__).parent.absolute()
        secrets_path = Path(f"{current_path}/../../../secrets")

        if file_path == "":
            file_path = f"{secrets_path}/spotify_credentials.json"
        with open(file_path, encoding="UTF-8") as secrets_file:
            try:
                data = json.loads(secrets_file.read())
            except json.JSONDecodeError as e:
                msg = "Invalid spotify_credentials.json format"
                raise TypeError(msg) from e

            credentials = [SpotifyCredentialPair(
                client_id=cred["client_id"],
                client_secret=cred["client_secret"],
            ) for cred in data]

            if len(credentials) == 0:
                msg = "No Spotify credentials found in configuration file"
                raise ValueError(msg)

            return cls(credentials=credentials)
