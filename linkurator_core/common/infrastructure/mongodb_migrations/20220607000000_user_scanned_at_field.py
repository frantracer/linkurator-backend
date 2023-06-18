# pylint: disable=invalid-name
from datetime import datetime

from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self):
        self.db.get_collection("users").update_many({}, {"$set": {"scanned_at": datetime.fromtimestamp(0)}})

    def downgrade(self):
        self.db.get_collection("users").update_many({}, {"$unset": {"scanned_at": ""}})
