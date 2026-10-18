from responseflow_local.domain.models import MessageView

REQUEST_PREFIXES = (
    "подскажите",
    "уточните",
    "пришлите",
    "когда",
    "можно",
)


def is_customer_request(message: MessageView) -> bool:
    if message.sender_role != "customer":
        return False

    normalized = message.text.strip().lower()

    return (
        "?" in normalized
        or normalized.startswith(REQUEST_PREFIXES)
        or "ждём ответ" in normalized
    )