# pylint: disable=invalid-name
from datetime import datetime, timezone
from typing import Any

from mongodb_migrations.base import BaseMigration  # type: ignore


class Migration(BaseMigration):
    def upgrade(self) -> None:
        followed_topics_collection = self.db.get_collection("followed_topics")
        users_collection = self.db.get_collection("users")

        topics_per_user: dict[Any, list[Any]] = {}
        followed_topic_items = followed_topics_collection.find()
        for item in followed_topic_items:
            user_id = item["user_uuid"]
            topic_id = item["topic_uuid"]
            if user_id not in topics_per_user:
                topics_per_user[user_id] = []
            topics_per_user[user_id].append(topic_id)

        for user_id, topic_ids in topics_per_user.items():
            users_collection.update_one({"uuid": user_id}, {"$set": {"followed_topics": topic_ids}})

        self.db.drop_collection("followed_topics")

    def downgrade(self) -> None:
        followed_topics_collection = self.db.get_collection("followed_topics")
        users_collection = self.db.get_collection("users")

        topics_per_user: dict[Any, list[dict[Any, Any]]] = {}
        users = users_collection.find()
        for user in users:
            user_id = user["uuid"]
            followed_topics = user["followed_topics"]
            for topic_id in followed_topics:
                if user_id not in topics_per_user:
                    topics_per_user[user_id] = []
                topics_per_user[user_id].append({
                    "user_uuid": user_id,
                    "topic_uuid": topic_id,
                    "created_at": datetime.now(tz=timezone.utc)
                })

        for _user_id, topic_ids in topics_per_user.items():
            followed_topics_collection.insert_many(topic_ids)

        users_collection.update_many({}, {"$unset": {"followed_topics": ""}})
