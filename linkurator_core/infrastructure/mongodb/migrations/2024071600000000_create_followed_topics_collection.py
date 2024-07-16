# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.create_collection("followed_topics")
        self.db.get_collection("followed_topics").create_index(("user_uuid", "topic_uuid"), unique=True)
        self.db.get_collection("followed_topics").create_index("user_uuid")
        self.db.get_collection("followed_topics").create_index("topic_uuid")

    def downgrade(self) -> None:
        self.db.drop_collection("followed_topics")
