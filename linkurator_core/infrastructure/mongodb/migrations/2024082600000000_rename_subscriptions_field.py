# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("users").update_many(
            {},
            {"$rename": {"subscription_uuids": "youtube_subscription_uuids"}})

    def downgrade(self) -> None:
        self.db.get_collection("users").update_many(
            {},
            {"$rename": {"youtube_subscription_uuids": "subscription_uuids"}})
