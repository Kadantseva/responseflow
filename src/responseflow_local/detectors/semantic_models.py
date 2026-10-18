from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SemanticResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal[
        "complaint",
        "document_request",
        "manager_attention",
    ]
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=10, max_length=240)
    recommended_action: str = Field(min_length=10, max_length=300)
    evidence_message_ids: tuple[str, ...]
    subject_key: str = Field(min_length=1)


class AnalysisReport(BaseModel):
    accepted: tuple[SemanticResult, ...]
    below_threshold: int
    invalid: int
    errors: tuple[str, ...]