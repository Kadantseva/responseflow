
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


FindingStatus = Literal[
    "open",
    "acknowledged",
    "snoozed",
    "resolved",
    "rejected",
    "reopened",
]


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: UUID
    workspace_id: str
    conversation_id: str
    project_id: str
    type: str
    subject_key: str
    deduplication_key: str
    status: FindingStatus = "open"
    version: int = Field(default=1, ge=1)
    summary: str
    recommended_action: str
    confidence: float = Field(ge=0, le=1)
    first_detected_at: AwareDatetime
    last_detected_at: AwareDatetime
    occurrence_count: int = Field(ge=1)
    due_at: AwareDatetime | None = None
    snoozed_until: AwareDatetime | None = None


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: UUID
    message_external_id: str
    added_at: AwareDatetime


class FindingEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    finding_id: UUID
    event_type: str
    occurred_at: AwareDatetime
    details: str
