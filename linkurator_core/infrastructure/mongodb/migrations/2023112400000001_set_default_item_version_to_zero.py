# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        # set default version to 0
        self.db.get_collection("items").update_many(
            {"version": None},
            {"$set": {"version": 0}},
        )

    def downgrade(self) -> None:
        self.db.get_collection("items").update_many(
            {"version": 0},
            {"$set": {"version": None}},
        )
