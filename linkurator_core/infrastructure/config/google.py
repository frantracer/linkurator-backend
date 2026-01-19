import json

from pydantic import BaseModel


class GoogleWebCredentials(BaseModel):
    client_id: str
    project_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_secret: str
    redirect_uris: list[str]
    javascript_origins: list[str]


class GoogleOAuth(BaseModel):
    web: GoogleWebCredentials


class GoogleSettings(BaseModel):
    gemini_api_key: str
    youtube_api_keys: list[str]
    oauth: GoogleOAuth
    email_service_credentials: dict[str, str]
    service_account_email: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "GoogleSettings":
        with open(config_file_path, encoding="UTF-8") as secrets_file:
            secrets = json.loads(secrets_file.read())["google"]

        return cls(
            gemini_api_key=secrets["gemini_api_key"],
            youtube_api_keys=secrets["youtube_api_keys"],
            oauth=GoogleOAuth(**secrets["oauth"]),
            email_service_credentials=secrets["email_service_credentials"],
            service_account_email=secrets["service_account_email"],
        )
