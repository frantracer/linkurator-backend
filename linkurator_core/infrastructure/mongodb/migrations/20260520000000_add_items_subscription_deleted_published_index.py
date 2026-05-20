# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("items").create_index(
            [("subscription_uuid", 1), ("deleted_at", 1), ("published_at", -1)],
        )
        self.db.get_collection("items").drop_index("deleted_at_1_provider_1")

    def downgrade(self) -> None:
        self.db.get_collection("items").create_index(
            [("deleted_at", 1), ("provider", 1)],
        )
        self.db.get_collection("items").drop_index(
            [("subscription_uuid", 1), ("deleted_at", 1), ("published_at", -1)],
        )
