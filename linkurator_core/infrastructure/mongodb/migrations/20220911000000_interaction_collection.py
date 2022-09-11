# pylint: disable=invalid-name

from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self):
        self.db.create_collection("interactions")
        self.db.get_collection("interactions").create_index("uuid", unique=True)
        self.db.get_collection("interactions").create_index("item_uuid")
        self.db.get_collection("interactions").create_index("user_uuid")

    def downgrade(self):
        self.db.drop_collection("interactions")
