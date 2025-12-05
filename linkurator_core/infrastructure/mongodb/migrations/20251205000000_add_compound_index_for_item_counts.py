# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        # Create compound index for efficient counting by deleted_at and provider
        self.db.get_collection("items").create_index([("deleted_at", 1), ("provider", 1)])

    def downgrade(self) -> None:
        self.db.get_collection("items").drop_index([("deleted_at", 1), ("provider", 1)])
