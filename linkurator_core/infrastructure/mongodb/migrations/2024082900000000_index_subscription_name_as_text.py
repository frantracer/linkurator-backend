# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("subscriptions").create_index([("name", "text")])

    def downgrade(self) -> None:
        self.db.get_collection("subscriptions").drop_index("name_text")
