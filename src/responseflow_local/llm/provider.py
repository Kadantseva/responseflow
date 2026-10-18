from typing import Protocol

from pydantic import BaseModel, ConfigDict

from .models import LlmCallResult


class LlmMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    content: str


class LlmRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: tuple[LlmMessage, ...]
    tool_name: str
    tool_description: str
    tool_parameters: dict
    max_output_tokens: int


class LlmProvider(Protocol):
    def complete(self, request: LlmRequest) -> LlmCallResult: ...