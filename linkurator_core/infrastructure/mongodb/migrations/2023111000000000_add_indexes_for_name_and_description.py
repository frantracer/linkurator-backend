# pylint: disable=invalid-name
import pymongo
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self):
        self.db.get_collection("items").create_index(
            [("name", pymongo.TEXT)],
            name="name_text_index",
            default_language="none",
        )

    def downgrade(self):
        self.db.get_collection("items").drop_index("name_text_index")
