import logging
from uuid import UUID

from linkurator_core.domain.chats.chat import Chat


def parse_ids_to_uuids(ids: list[str] | None) -> list[UUID]:
    if ids is None:
        return []

    valid_uuids: list[UUID] = []
    for id_str in ids:
        try:
            valid_uuids.append(UUID(id_str))
        except ValueError as e:
            logging.exception(f"Failed to parse UUID {id_str}: {e}")

    return valid_uuids


def build_chat_context(previous_chat: Chat | None) -> str:
    context = ""
    if previous_chat is not None and len(previous_chat.messages) > 0:
        context = "Previous chat messages:\n"
        for message in previous_chat.messages:
            if message.role == "user":
                context += f"User: {message.content}\n"
            elif message.role == "assistant":
                context += f"Assistant: {message.content}\n"
        context += "End of previous chat messages.\n"
    return context
