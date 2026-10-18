
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from responseflow_local.storage.models import Finding, FindingEvent
from responseflow_local.storage.repositories import FindingRepository


class FindingNotFoundError(LookupError):
    pass


class VersionConflictError(ValueError):
    pass


class InvalidTransitionError(ValueError):
    pass


class InvalidDecisionError(ValueError):
    pass


RejectionReason = Literal[
    "not_actionable",
    "wrong_type",
    "already_resolved",
    "insufficient_evidence",
]


class DecisionBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    author: str = Field(min_length=1, max_length=200)
    expected_version: int = Field(ge=1)
    occurred_at: AwareDatetime


class AcknowledgeRequest(DecisionBase):
    comment: str = Field(
        default="Принято в работу",
        max_length=2000,
    )


class SnoozeRequest(DecisionBase):
    until: AwareDatetime
    reason: str = Field(min_length=3, max_length=2000)


class ResolveRequest(DecisionBase):
    comment: str = Field(min_length=10, max_length=2000)


class RejectRequest(DecisionBase):
    reason_code: RejectionReason
    comment: str = Field(min_length=10, max_length=2000)


class InboxService:
    ALLOWED_TRANSITIONS = {
        "acknowledge": {
            "open": "acknowledged",
            "reopened": "acknowledged",
        },
        "snooze": {
            "open": "snoozed",
            "reopened": "snoozed",
            "acknowledged": "snoozed",
        },
        "resolve": {
            "open": "resolved",
            "reopened": "resolved",
            "acknowledged": "resolved",
        },
        "reject": {
            "open": "rejected",
            "reopened": "rejected",
            "acknowledged": "rejected",
        },
    }

    def __init__(self, repository: FindingRepository) -> None:
        self._repository = repository

    def _get(
        self,
        workspace_id: str,
        finding_id: UUID,
    ) -> Finding:
        finding = self._repository.find_by_id(finding_id)

        if finding is None or finding.workspace_id != workspace_id:
            raise FindingNotFoundError(str(finding_id))

        return finding

    def get_finding(
        self,
        workspace_id: str,
        finding_id: UUID,
    ) -> Finding:
        return self._get(workspace_id, finding_id)

    def list_findings(
        self,
        workspace_id: str,
        status: str | None = None,
        priority: str | None = None,
        project_id: str | None = None,
    ) -> tuple[Finding, ...]:
        # Для списка добавим отдельный метод репозитория.
        items = self._repository.list_for_workspace(workspace_id)

        if status is not None:
            items = tuple(item for item in items if item.status == status)

        if project_id is not None:
            items = tuple(
                item for item in items if item.project_id == project_id
            )

        if priority is not None:
            items = tuple(
                item for item in items if priority in item.flags
            )

        return tuple(sorted(
            items,
            key=lambda item: (
                item.due_at is None,
                item.due_at or item.first_detected_at,
                str(item.finding_id),
            ),
        ))

    def get_history(
        self,
        workspace_id: str,
        finding_id: UUID,
    ) -> tuple[FindingEvent, ...]:
        self._get(workspace_id, finding_id)
        return self._repository.list_events(finding_id)

    
    def _decide(
        self,
        workspace_id: str,
        finding_id: UUID,
        command: DecisionBase,
        action: str,
        comment: str,
        snoozed_until: datetime | None = None,
        reason_code: str | None = None,
    ) -> Finding:
        if not command.author.strip():
            raise InvalidDecisionError(
                "Автор решения не может быть пустым"
            )

        if action == "snooze":
            if snoozed_until is None:
                raise InvalidDecisionError("Не задан срок snooze")

            if snoozed_until <= datetime.now(timezone.utc):
                raise InvalidDecisionError(
                    "Время snooze должно быть в будущем"
                )

        if action not in self.ALLOWED_TRANSITIONS:
            raise InvalidDecisionError(
                f"Неизвестное решение: {action}"
            )

        with self._repository.transaction():
            finding = self._get(workspace_id, finding_id)

            if finding.version != command.expected_version:
                raise VersionConflictError(
                    "Карточка уже была изменена"
                )

            target_status = self.ALLOWED_TRANSITIONS[action].get(
                finding.status
            )

            if target_status is None:
                raise InvalidTransitionError(
                    f"Нельзя выполнить {action} "
                    f"из {finding.status}"
                )

            updated = finding.model_copy(
                update={
                    "status": target_status,
                    "version": finding.version + 1,
                    "snoozed_until": (
                        snoozed_until if action == "snooze" else None
                    ),
                },
                deep=True,
            )

            details = json.dumps(
                {
                    "author": command.author.strip(),
                    "comment": comment,
                    "from_status": finding.status,
                    "to_status": target_status,
                    "version": updated.version,
                    "expected_version": command.expected_version,
                    "reason_code": reason_code,
                    "snoozed_until": (
                        snoozed_until.isoformat()
                        if snoozed_until is not None
                        else None
                    ),
                },
                ensure_ascii=False,
            )

            event = FindingEvent(
                event_id=uuid4(),
                finding_id=finding_id,
                event_type=action,
                occurred_at=command.occurred_at,
                details=details,
            )

            self._repository.save_finding(updated)
            self._repository.add_event(event)

        return updated


    def acknowledge(
        self,
        workspace_id: str,
        finding_id: UUID,
        command: AcknowledgeRequest,
    ) -> Finding:
        return self._decide(
            workspace_id, finding_id, command,
            "acknowledge", command.comment,
        )

    def snooze(
        self,
        workspace_id: str,
        finding_id: UUID,
        command: SnoozeRequest,
    ) -> Finding:
        return self._decide(
            workspace_id, finding_id, command,
            "snooze", command.reason, command.until,
        )

    def resolve(
        self,
        workspace_id: str,
        finding_id: UUID,
        command: ResolveRequest,
    ) -> Finding:
        return self._decide(
            workspace_id, finding_id, command,
            "resolve", command.comment,
        )

    def reject(
        self,
        workspace_id: str,
        finding_id: UUID,
        command: RejectRequest,
    ) -> Finding:
        return self._decide(
            workspace_id, finding_id, command,
            "reject",
            f"{command.reason_code}: {command.comment}",
            reason_code=command.reason_code,
        )
