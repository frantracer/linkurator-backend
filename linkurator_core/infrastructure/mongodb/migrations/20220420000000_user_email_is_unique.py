# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("users").create_index("email", unique=True, name="email_unique")

    def downgrade(self) -> None:
        self.db.get_collection("users").drop_index("email_unique")
