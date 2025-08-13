from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from linkurator_core.domain.chats.chat import Chat, ChatMessage
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


@dataclass
class EnrichedChatMessage:
    message: ChatMessage
    items: list[Item]
    subscriptions: list[Subscription]
    topics: list[Topic]


@dataclass
class EnrichedChat:
    chat: Chat
    enriched_messages: list[EnrichedChatMessage]


class GetChatHandler:
    def __init__(
        self,
        chat_repository: ChatRepository,
        item_repository: ItemRepository,
        subscription_repository: SubscriptionRepository,
        topic_repository: TopicRepository,
    ) -> None:
        self.chat_repository = chat_repository
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository
        self.topic_repository = topic_repository

    async def handle(self, chat_id: UUID, user_id: UUID) -> Optional[EnrichedChat]:
        chat = await self.chat_repository.get(chat_id)
        if chat is None or chat.user_id != user_id:
            return None

        # Enrich chat messages with referenced objects
        enriched_messages = []
        for message in chat.messages:
            # Collect all UUIDs from the message
            all_item_uuids = set(message.item_uuids)
            all_subscription_uuids = set(message.subscription_uuids)
            all_topic_uuids = set(message.topic_uuids)

            # Fetch referenced objects
            items = []
            if all_item_uuids:
                items = await self.item_repository.find_items(
                    criteria=ItemFilterCriteria(item_ids=all_item_uuids),
                    page_number=0,
                    limit=len(all_item_uuids),
                )

            subscriptions = []
            if all_subscription_uuids:
                subscriptions = await self.subscription_repository.get_list(list(all_subscription_uuids))

            topics = []
            if all_topic_uuids:
                topics = await self.topic_repository.find_topics(list(all_topic_uuids))

            enriched_message = EnrichedChatMessage(
                message=message,
                items=items,
                subscriptions=subscriptions,
                topics=topics,
            )
            enriched_messages.append(enriched_message)

        return EnrichedChat(
            chat=chat,
            enriched_messages=enriched_messages,
        )
