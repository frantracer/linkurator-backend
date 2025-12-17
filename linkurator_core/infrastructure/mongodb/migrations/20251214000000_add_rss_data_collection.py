# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        self.db.create_collection("rss_data")
        self.db.get_collection("rss_data").create_index(
            [("rss_url", 1), ("item_url", 1)],
            unique=True,
        )

    def downgrade(self) -> None:
        self.db.drop_collection("rss_data")
