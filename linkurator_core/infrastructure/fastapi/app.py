"""
Main file of the application
"""
import json
import os

from fastapi.applications import FastAPI

from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.application.register_user_handler import RegisterUserHandler
from linkurator_core.application.validate_token_handler import ValidateTokenHandler
from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.mongodb.session_repository import MongoDBSessionRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository

google_client_secret_path = os.environ.get('LINKURATOR_GOOGLE_SECRET_PATH', "client_secret.json")
with open(google_client_secret_path, "r", encoding='UTF-8') as secrets_file:
    secrets = json.loads(secrets_file.read())
    client_id = secrets["web"]["client_id"]
    client_secret = secrets["web"]["client_secret"]
account_service = GoogleAccountService(
    client_id=client_id,
    client_secret=client_secret)

db_settings = MongoDBSettings()
user_repository = MongoDBUserRepository(ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name)
session_repository = MongoDBSessionRepository(ip=db_settings.address, port=db_settings.port,
                                              db_name=db_settings.db_name)

app_handlers = Handlers(
    register_user=RegisterUserHandler(user_repository, account_service),
    validate_token=ValidateTokenHandler(user_repository, session_repository, account_service),
    google_client=account_service
)

# FastAPI application
app: FastAPI = create_app(app_handlers)
