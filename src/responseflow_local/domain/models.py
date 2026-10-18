from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, field_validator


class Participant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    participant_id: str
    display_name: str
    role: Literal["customer", "employee", "system"]
    organization_id: str | None


class Project(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    project_id: str
    conversation_id: str
    organization_id: str
    organization_name: str
    project_name: str
    service_tier: Literal["key", "standard"]
    response_sla_minutes: int = Field(gt=0)
    responsible_role: str

class MessageView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    external_id: str
    revision: int
    sender_role: Literal["customer", "employee", "system"]
    sender_name: str
    sent_at: AwareDatetime
    text: str
    reply_to_external_id: str | None = None



class ConversationWindow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    workspace_id: str
    conversation_id: str
    project_id: str
    analysis_time: AwareDatetime
    messages: tuple[MessageView, ...]
    response_sla_minutes: int = Field(gt=0)
    omitted_before: int = 0


class MessageRevision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    sender_id: str = Field(min_length=1)
    sender_role: Literal["customer", "employee", "system"]
    sent_at: datetime
    observed_at: datetime
    text: str = Field(min_length=1)
    reply_to_external_id: str | None = None
    source: Literal["telegram", "max", "import"]

    @field_validator("sent_at", "observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must contain timezone info")
        return value

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text cannot be empty or only whitespace")
        return value