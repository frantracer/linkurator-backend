# pylint: disable=invalid-name

from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self):
        self.db.get_collection("items").create_index("url")

    def downgrade(self):
        self.db.get_collection("items").drop_index("url")
