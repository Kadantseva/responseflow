from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict


class MessageView(BaseModel):
    model_config = ConfigDict(frozen=True)

    external_id: str
    sender_role: Literal["customer", "employee", "system"]
    sent_at: AwareDatetime
    text: str
    reply_to_external_id: str | None = None


class CommitmentCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["commitment", "delay"]
    subject_key: str
    summary: str
    due_at: AwareDatetime
    commitment_message_id: str
    completion_message_id: str | None = None
    evidence_message_ids: tuple[str, ...]
    responsible_role: Literal["account_manager"] = "account_manager"