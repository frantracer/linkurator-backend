# pylint: disable=invalid-name

from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("items").create_index("published_at")
        self.db.get_collection("items").create_index("created_at")

    def downgrade(self) -> None:
        self.db.get_collection("items").drop_index("published_at")
        self.db.get_collection("items").drop_index("created_at")
