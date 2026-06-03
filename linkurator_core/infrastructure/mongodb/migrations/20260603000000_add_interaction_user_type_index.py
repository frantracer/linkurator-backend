# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        # Compound index to efficiently filter a user's interactions by type
        # (used when finding viewed/recommended/discouraged/hidden items)
        self.db.get_collection("interactions").create_index([("user_uuid", 1), ("type", 1)])

    def downgrade(self) -> None:
        self.db.get_collection("interactions").drop_index([("user_uuid", 1), ("type", 1)])
