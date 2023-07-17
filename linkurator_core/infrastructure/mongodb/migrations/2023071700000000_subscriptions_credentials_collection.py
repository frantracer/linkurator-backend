# pylint: disable=invalid-name

from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self):
        self.db.create_collection("subscriptions_credentials")
        self.db.get_collection("subscriptions_credentials").create_index("user_id", unique=True)

    def downgrade(self):
        self.db.drop_collection("subscriptions_credentials")
