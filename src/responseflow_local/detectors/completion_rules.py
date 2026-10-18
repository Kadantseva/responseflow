ACTION_WORDS = ("пришлю", "отправлю", "подготовлю", "исправлю", "сообщу")
COMPLETION_WORDS = (
    "отправил", "отправила", "направил", "направила", "готово", "исправлено"
)
FOLLOW_UP_PHRASES = ("не получили", "всё ещё нет", "когда сможете")

def contains_word(text: str, words: tuple[str, ...]) -> bool:
    normalized_words = set(text.lower().replace(".", " ").split())
    return any(word in normalized_words for word in words)


def has_action_word(text: str) -> bool:
    return contains_word(text, ACTION_WORDS)


def is_completion_text(text: str) -> bool:
    return contains_word(text, COMPLETION_WORDS)

def is_unresolved_follow_up(text: str) -> bool:
    normalized = text.lower()
    return any(phrase in normalized for phrase in FOLLOW_UP_PHRASES)