from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


FindingType = Literal[
    "unanswered",
    "commitment",
    "complaint",
    "document_request",
    "manager_attention",
]

class DetectorRun(BaseModel):
    model_config = ConfigDict(frozen=True)
    detector_name: str
    detector_version: str
    status: Literal["succeeded", "failed"]
    candidate_count: int = Field(ge=0)
    error: str | None = None


class AnalysisRunReport(BaseModel):
    workspace_id: str
    analysis_time: AwareDatetime
    detector_runs: tuple[DetectorRun, ...]
    created_findings: int
    updated_findings: int

class FindingCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    conversation_id: str
    project_id: str

    type: FindingType
    subject_key: str
    summary: str
    recommended_action: str
    confidence: float = Field(ge=0, le=1)
    evidence_message_ids: tuple[str, ...]

    detected_at: AwareDatetime
    due_at: AwareDatetime | None = None
    waiting_minutes: int = Field(default=0, ge=0)
    flags: tuple[str, ...] = ()