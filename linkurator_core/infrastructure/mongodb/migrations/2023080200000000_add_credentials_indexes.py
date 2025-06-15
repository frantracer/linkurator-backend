# pylint: disable=invalid-name

from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        # add index for tuple (credential_type, value)
        self.db.get_collection("subscriptions_credentials").create_index(
            [("credential_type", 1), ("value", 1)], unique=True,
        )

    def downgrade(self) -> None:
        self.db.get_collection("subscriptions_credentials").drop_index(
            [("credential_type", 1), ("value", 1)],
        )
