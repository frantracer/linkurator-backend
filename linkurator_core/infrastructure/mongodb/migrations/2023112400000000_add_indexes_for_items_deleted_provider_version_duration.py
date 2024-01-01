# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("items").create_index("deleted_at")
        self.db.get_collection("items").create_index("provider")
        self.db.get_collection("items").create_index("version")
        self.db.get_collection("items").create_index("duration")

    def downgrade(self) -> None:
        self.db.get_collection("items").drop_index("deleted_at")
        self.db.get_collection("items").drop_index("provider")
        self.db.get_collection("items").drop_index("version")
        self.db.get_collection("items").drop_index("duration")
