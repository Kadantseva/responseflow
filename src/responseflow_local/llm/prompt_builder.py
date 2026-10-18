from pathlib import Path

from responseflow_local.domain.models import ConversationWindow
from .provider import LlmMessage, LlmRequest
from .tool_schema import situation_tool_schema


def render_conversation(window: ConversationWindow) -> str:
    lines: list[str] = []
    for message in window.messages:
        safe_text = message.text.replace("\x00", "")
        lines.append(
            f"[{message.external_id}] {message.sent_at} "
            f"{message.sender_role}: {safe_text}"
        )
    return "\n".join(lines)


def build_request(window: ConversationWindow, project_context: str,
                  system_prompt_path: Path,
                  max_output_tokens: int) -> LlmRequest:
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    user_content = (
        "ПРОЕКТНЫЙ КОНТЕКСТ\n"
        f"{project_context}\n\n"
        "ПЕРЕПИСКА\n"
        f"{render_conversation(window)}"
    )
    tool = situation_tool_schema()["function"]
    return LlmRequest(
        messages=(
            LlmMessage(role="system", content=system_prompt),
            LlmMessage(role="user", content=user_content),
        ),
        tool_name=tool["name"],
        tool_description=tool["description"],
        tool_parameters=tool["parameters"],
        max_output_tokens=max_output_tokens,
    )