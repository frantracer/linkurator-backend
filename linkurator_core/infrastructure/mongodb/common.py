from typing import Any

MongoDBMapping = dict[str, Any]


def normalize_text_search(text: str) -> str:
    text = text.replace('"', " ")
    return " ".join([f'"{word}"' for word in text.split(" ") if len(word) > 0])


def extract_keywords_from_text(text: str) -> list[str]:
    stop_words = {
        # Spanish stop words
        "de", "del", "la", "el", "un", "una", "al",
        # English stop words
        "of", "the", "a", "an",
    }
    keywords = text.strip().replace('"', "").replace("'", "").split(" ")
    return [keyword for keyword in keywords if len(keyword) > 1 and keyword.lower() not in stop_words]
