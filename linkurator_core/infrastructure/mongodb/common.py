from typing import Any

MongoDBMapping = dict[str, Any]


def normalize_text_search(text: str) -> str:
    text = text.replace('"', " ")
    return " ".join([f'"{word}"' for word in text.split(" ") if len(word) > 0])
