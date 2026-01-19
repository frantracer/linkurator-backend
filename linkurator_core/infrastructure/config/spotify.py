import json

from pydantic import BaseModel


class SpotifyCredentialPair(BaseModel):
    client_id: str
    client_secret: str


class SpotifyClientSecrets(BaseModel):
    credentials: list[SpotifyCredentialPair]

    @classmethod
    def from_file(cls, file_path: str) -> "SpotifyClientSecrets":
        """
        Load Spotify credentials from a JSON file.
        :param file_path:
        :return:
        """
        with open(file_path, encoding="UTF-8") as secrets_file:
            secrets = json.loads(secrets_file.read())["spotify"]['credentials']

            credentials = [SpotifyCredentialPair(
                client_id=cred["client_id"],
                client_secret=cred["client_secret"],
            ) for cred in secrets]

            if len(credentials) == 0:
                msg = "No Spotify credentials found in configuration file"
                raise ValueError(msg)

            return cls(credentials=credentials)
