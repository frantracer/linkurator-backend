# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        # set default provider to youtube
        self.db.get_collection("items").update_many(
            {"provider": None},
            {"$set": {"provider": "youtube"}},
        )

    def downgrade(self) -> None:
        self.db.get_collection("items").update_many(
            {"provider": "youtube"},
            {"$set": {"provider": None}},
        )
