# pylint: disable=invalid-name
from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        for user in self.db.get_collection("users").find():
            username = str(user["first_name"] + user["last_name"]).strip().replace(" ", "").lower()
            self.db.get_collection("users").update_one(
                {"_id": user["_id"]},
                {"$set": {"username": username}}
            )
        self.db.get_collection("users").create_index("username", unique=True)

    def downgrade(self) -> None:
        self.db.get_collection("users").update_many({}, {"$unset": {"username": ""}})
