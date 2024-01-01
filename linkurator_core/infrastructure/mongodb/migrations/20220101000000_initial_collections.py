# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.create_collection("items")
        self.db.get_collection("items").create_index("uuid", unique=True)
        self.db.get_collection("items").create_index("subscription_uuid")

        self.db.create_collection("subscriptions")
        self.db.get_collection("subscriptions").create_index("uuid", unique=True)

        self.db.create_collection("topics")
        self.db.get_collection("topics").create_index("uuid", unique=True)

        self.db.create_collection("users")
        self.db.get_collection("users").create_index("uuid", unique=True)

    def downgrade(self) -> None:
        self.db.drop_collection("items")
        self.db.drop_collection("subscriptions")
        self.db.drop_collection("topics")
        self.db.drop_collection("users")
