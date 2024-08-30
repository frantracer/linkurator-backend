# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.create_collection("registration_requests")
        self.db.get_collection("registration_requests").create_index("uuid", unique=True)

    def downgrade(self) -> None:
        self.db.drop_collection("registration_requests")
