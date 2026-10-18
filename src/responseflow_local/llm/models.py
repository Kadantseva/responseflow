from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

class LlmSituation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    type: Literal[
        "unanswered", "commitment", "complaint",
        "document_request", "manager_attention"
    ]
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=10, max_length=240)
    recommended_action: str = Field(min_length=10, max_length=300)
    evidence_message_ids: tuple[str, ...] = Field(min_length=1)
    subject_key: str = Field(min_length=1, max_length=160)


class LlmAnalysisPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    situations: tuple[LlmSituation, ...]


class LlmUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None


class LlmCallResult(BaseModel):
    provider: str
    model: str
    raw_arguments: str
    usage: LlmUsage


class AnalysisResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    situations: tuple[LlmSituation, ...]
    provider: str
    model: str
    prompt_version: str
    usage: LlmUsage