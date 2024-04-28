# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("users").drop_index("email_unique")
        self.db.get_collection("users").create_index(
            [("email", 1), ("deleted_at", 1)],
            unique=True,
            name="email_unique"
        )
        self.db.get_collection("users").create_index("deleted_at")

    def downgrade(self) -> None:
        self.db.get_collection("users").drop_index("email_unique")
        self.db.get_collection("users").drop_index("deleted_at")
        self.db.get_collection("users").create_index("email", unique=True, name="email_unique")
