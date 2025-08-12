# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.create_collection("chats")
        self.db.get_collection("chats").create_index("uuid", unique=True)
        self.db.get_collection("chats").create_index("user_id")
        self.db.get_collection("chats").create_index("created_at")

    def downgrade(self) -> None:
        self.db.drop_collection("chats")
