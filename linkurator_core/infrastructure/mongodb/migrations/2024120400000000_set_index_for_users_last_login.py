# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.get_collection("users").create_index("last_login_at")

    def downgrade(self) -> None:
        self.db.get_collection("users").drop_index("last_login_at")
