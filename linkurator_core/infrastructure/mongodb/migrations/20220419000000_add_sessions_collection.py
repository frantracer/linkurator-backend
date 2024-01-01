# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.create_collection("sessions")
        self.db.get_collection("sessions").create_index("token", unique=True)

    def downgrade(self) -> None:
        self.db.drop_collection("sessions")
