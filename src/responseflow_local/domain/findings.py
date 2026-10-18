from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(frozen=True)
    type: Literal["unanswered"] = "unanswered"
    subject_key: str
    summary: str
    evidence_message_ids: tuple[str, ...]
    waiting_minutes: int = Field(ge=0)
    due_at: AwareDatetime