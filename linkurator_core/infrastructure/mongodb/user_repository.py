from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from linkurator_core.domain.common import utils
from linkurator_core.domain.users.user import HashedPassword, User, Username
from linkurator_core.domain.users.user_repository import EmailAlreadyInUse, UserRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBHashedPassword(BaseModel):
    hashed_pass_plus_salt: str
    salt: str

    @staticmethod
    def from_domain_password_hash(password_hash: HashedPassword) -> MongoDBHashedPassword:
        return MongoDBHashedPassword(
            hashed_pass_plus_salt=password_hash.hashed_pass_plus_salt,
            salt=password_hash.salt,
        )

    def to_domain_password_hash(self) -> HashedPassword:
        return HashedPassword(
            hashed_pass_plus_salt=self.hashed_pass_plus_salt,
            salt=self.salt,
        )


class MongoDBUser(BaseModel):
    uuid: UUID
    first_name: str
    last_name: str
    username: str
    email: str
    locale: str = "en"
    avatar_url: str = "https://www.linkurator.com/favicon.ico"
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    last_login_at: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    google_refresh_token: str | None = None
    subscription_uuids: list[UUID] = []
    youtube_subscription_uuids: list[UUID] = []
    youtube_unfollowed_subscription_uuids: list[UUID] = []
    is_admin: bool = False
    curators: list[UUID] = []
    followed_topics: list[UUID] = []
    favorite_topics: list[UUID] = []
    password_hash: MongoDBHashedPassword | None = None

    @staticmethod
    def from_domain_user(user: User) -> MongoDBUser:
        return MongoDBUser(
            uuid=user.uuid,
            first_name=user.first_name,
            last_name=user.last_name,
            username=str(user.username),
            email=user.email,
            locale=user.locale,
            avatar_url=str(user.avatar_url),
            created_at=user.created_at,
            updated_at=user.updated_at,
            scanned_at=user.scanned_at,
            last_login_at=user.last_login_at,
            google_refresh_token=user.google_refresh_token,
            subscription_uuids=list(user.get_subscriptions(include_youtube=False)),
            youtube_subscription_uuids=list(user.get_youtube_subscriptions()),
            youtube_unfollowed_subscription_uuids=list(user.get_youtube_unfollowed_subscriptions()),
            followed_topics=list(user.get_followed_topics()),
            favorite_topics=list(user.get_favorite_topics()),
            is_admin=user.is_admin,
            curators=list(user.curators),
            password_hash=None if user.password_hash is None
            else MongoDBHashedPassword.from_domain_password_hash(user.password_hash),
        )

    def to_domain_user(self) -> User:
        return User(
            uuid=self.uuid,
            first_name=self.first_name,
            last_name=self.last_name,
            username=Username(self.username),
            email=self.email,
            locale=self.locale,
            avatar_url=utils.parse_url(self.avatar_url),
            created_at=self.created_at,
            updated_at=self.updated_at,
            scanned_at=self.scanned_at,
            last_login_at=self.last_login_at,
            google_refresh_token=self.google_refresh_token,
            _subscription_uuids=set(self.subscription_uuids),
            _youtube_subscriptions_uuids=set(self.youtube_subscription_uuids),
            _unfollowed_youtube_subscriptions_uuids=set(self.youtube_unfollowed_subscription_uuids),
            _followed_topics=set(self.followed_topics),
            _favorite_topics=set(self.favorite_topics),
            is_admin=self.is_admin,
            curators=set(self.curators),
            password_hash=None if self.password_hash is None
            else self.password_hash.to_domain_password_hash(),
        )


class MongoDBUserRepository(UserRepository):
    _collection_name: str = "users"
    _deleted_users_collection_name: str = "deleted_users"

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient[MongoDBMapping](
            f"mongodb://{ip!s}:{port}/", username=username, password=password)
        self.db_name = db_name

    def _collection(self) -> AsyncIOMotorCollection[MongoDBMapping]:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name, codec_options=codec_options).get_collection(self._collection_name)

    def _collection_for_deleted_users(self) -> AsyncIOMotorCollection[MongoDBMapping]:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name, codec_options=codec_options).get_collection(
            self._deleted_users_collection_name)

    async def check_connection(self) -> None:
        for collection_name in [self._collection_name, self._deleted_users_collection_name]:
            if collection_name not in await self.client[self.db_name].list_collection_names():
                msg = f"Collection '{collection_name}' is not initialized in database '{self.db_name}'"
                raise CollectionIsNotInitialized(
                    msg)

    async def add(self, user: User) -> None:
        try:
            await self._collection().insert_one(MongoDBUser.from_domain_user(user).model_dump())
        except DuplicateKeyError as error:
            if error.details is not None and "email_unique" in error.details.get("errmsg", ""):
                msg = f"Email '{user.email}' is already in use"
                raise EmailAlreadyInUse(msg) from error

    async def get(self, user_id: UUID) -> User | None:
        user = await self._collection().find_one({"uuid": user_id})
        if user is None:
            return None
        user.pop("_id", None)
        return MongoDBUser(**user).to_domain_user()

    async def get_all(self) -> list[User]:
        users = await self._collection().find({}).to_list(length=None)
        return [MongoDBUser(**user).to_domain_user() for user in users]

    async def get_by_email(self, email: str) -> User | None:
        user = await self._collection().find_one({"email": email})
        if user is None:
            return None
        user.pop("_id", None)
        return MongoDBUser(**user).to_domain_user()

    async def get_by_username(self, username: Username) -> User | None:
        user = await self._collection().find_one({"username": str(username)})
        if user is None:
            return None
        user.pop("_id", None)
        return MongoDBUser(**user).to_domain_user()

    async def delete(self, user_id: UUID) -> None:
        user = await self.get(user_id)
        if user is not None:
            user_dump = MongoDBUser.from_domain_user(user).model_dump()
            user_dump["deleted_at"] = datetime.now(timezone.utc)
            await self._collection_for_deleted_users().insert_one(user_dump)
            await self._collection().delete_one({"uuid": user_id})

    async def delete_all(self) -> None:
        users = await self.get_all()
        for user in users:
            await self.delete(user.uuid)

    async def update(self, user: User) -> None:
        await self._collection().update_one(
            {"uuid": user.uuid},
            {"$set": MongoDBUser.from_domain_user(user).model_dump()})

    async def find_latest_scan_before(self, timestamp: datetime) -> list[User]:
        users = await self._collection().find(
            {"scanned_at": {"$lt": timestamp}},
        ).to_list(length=None)
        return [MongoDBUser(**user).to_domain_user() for user in users]

    async def find_users_subscribed_to_subscription(self, subscription_id: UUID) -> list[User]:
        users = await self._collection().find(
            {
                "$or": [
                    {"subscription_uuids": subscription_id},
                    {"youtube_subscription_uuids": subscription_id},
                ],
            },
        ).to_list(length=None)
        return [MongoDBUser(**user).to_domain_user() for user in users]

    async def count_registered_users(self) -> int:
        return await self._collection().count_documents({})

    async def count_active_users(self) -> int:
        logged_after = User.time_since_last_active()
        return await self._collection().count_documents({"last_login_at": {"$gt": logged_after}})
