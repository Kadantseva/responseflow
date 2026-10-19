from datetime import datetime

from responseflow_local.detectors.business_time import add_working_minutes, working_minutes_between
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from .question_rules import is_customer_request
from responseflow_local.domain.findings import FindingCandidate


class MessageView(BaseModel):
    model_config = ConfigDict(frozen=True)

    external_id: str
    conversation_id: str
    sender_role: str
    sent_at: AwareDatetime
    text: str

class DetectionContext(BaseModel):
    workspace_id: str
    conversation_id: str
    response_sla_minutes: int = Field(gt=0)
    analysis_time: AwareDatetime
    messages: tuple[MessageView, ...]


REQUEST_PREFIXES = (
    "подскажите",
    "уточните",
    "пришлите",
    "когда",
    "можно",
)



def first_employee_reply_after(
    messages: tuple[MessageView, ...],
    request_index: int,
) -> MessageView | None:
    for message in messages[request_index + 1:]:
        if message.sender_role == "employee":
            return message

    return None


class UnansweredDetector:
    name = "unanswered"
    version = "unanswered-rules-1"

    def detect(
        self,
        window: DetectionContext,
    ) -> tuple[FindingCandidate, ...]:
        candidates: list[FindingCandidate] = []

        for index, message in enumerate(window.messages):
            if not is_customer_request(message):
                continue

            has_reply = any(
                later.sender_role == "employee"
                and later.sent_at <= window.analysis_time
                for later in window.messages[index + 1:]
            )
            if has_reply:
                continue
            try:
                due_at = add_working_minutes(
                    message.sent_at,
                    window.response_sla_minutes,
                )

            except Exception as e:
                print('ОШИБКА:', type(e).__name__, str(e))
                raise


            if window.analysis_time < due_at:
                continue
            
            try:
                waiting_minutes = working_minutes_between(
                                message.sent_at,
                                window.analysis_time,
                            )

            except Exception as e:
                print('ОШИБКА:', type(e).__name__, str(e))
                raise

            try:
                candidates.append(
                                FindingCandidate(
                                    workspace_id=window.workspace_id,
                                    conversation_id=window.conversation_id,
                                    project_id=window.project_id,
                                    type="unanswered",
                                    confidence=1.0,
                                    subject_key=message.external_id,
                                    summary=(
                                        f"Клиент ожидает ответа на сообщение "
                                        f"{message.external_id}. "
                                        f"Ожидание: {waiting_minutes} рабочих минут."
                                    ),
                                    recommended_action=(
                                        "Проверить обращение клиента "
                                        "и подготовить ответ."
                                    ),
                                    evidence_message_ids=(message.external_id,),
                                    detected_at=window.analysis_time,
                                    due_at=due_at,
                                    waiting_minutes=waiting_minutes
                                )
                            )

            except Exception as e:
                print('ОШИБКА:', type(e).__name__, str(e))
                raise
            
        return tuple(
            sorted(
                candidates,
                key=lambda item: (item.due_at, item.subject_key),
            )
        )