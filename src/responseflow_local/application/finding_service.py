
from uuid import UUID, uuid4
import traceback

from .key_builder import build_deduplication_key
from responseflow_local.domain.findings import FindingCandidate
# from responseflow_local.domain.models import Finding, FindingEvent, FindingStatus
from responseflow_local.storage.models import Evidence,Finding, FindingEvent, FindingStatus
from responseflow_local.storage.repositories import FindingRepository


class FindingService:
    def __init__(self, repository: FindingRepository) -> None:
        self._repository = repository

    
    def record(self, candidate: FindingCandidate) -> Finding:
        try:
            key = build_deduplication_key(
                candidate.workspace_id,
                candidate.conversation_id,
                candidate.type,
                candidate.subject_key,
            )

            with self._repository.transaction():
                existing = self._repository.find_by_key(
                    candidate.workspace_id,
                    key,
                )

                if existing is None:
                    return self._create(candidate, key)

                return self._update(existing, candidate)

        except Exception as e:
            print("ОШИБКА record:", type(e).__name__, str(e))
            traceback.print_exc()
            raise


    def _create(
        self,
        candidate: FindingCandidate,
        key: str,
    ) -> Finding:
        now = candidate.detected_at

        finding = Finding(
            finding_id=uuid4(),
            workspace_id=candidate.workspace_id,
            conversation_id=candidate.conversation_id,
            project_id=candidate.project_id,
            type=candidate.type,
            subject_key=candidate.subject_key,
            deduplication_key=key,
            status="open",
            summary=candidate.summary,
            recommended_action=candidate.recommended_action,
            confidence=candidate.confidence,
            first_detected_at=now,
            last_detected_at=now,
            occurrence_count=1,
            due_at=candidate.due_at
        )

        self._repository.save_finding(finding)

        for message_id in dict.fromkeys(candidate.evidence_message_ids):
            self._repository.add_evidence(
                Evidence(
                    finding_id=finding.finding_id,
                    message_external_id=message_id,
                    added_at=now,
                )
            )

        self._repository.add_event(
            FindingEvent(
                event_id=uuid4(),
                finding_id=finding.finding_id,
                event_type="created",
                occurred_at=now,
                details="Карточка создана при первом обнаружении",
            )
        )

        return finding

    def _update(
        self,
        existing: Finding,
        candidate: FindingCandidate,
    ) -> Finding:
        now = candidate.detected_at

        known_evidence = {
            item.message_external_id
            for item in self._repository.list_evidence(
                existing.finding_id
            )
        }

        new_evidence_ids = tuple(
            message_id
            for message_id in dict.fromkeys(
                candidate.evidence_message_ids
            )
            if message_id not in known_evidence
        )

        for message_id in new_evidence_ids:
            self._repository.add_evidence(
                Evidence(
                    finding_id=existing.finding_id,
                    message_external_id=message_id,
                    added_at=now,
                )
            )

        status = existing.status
        reopened = (
            bool(new_evidence_ids)
            and status in {"resolved", "rejected"}
        )

        if reopened:
            status = "reopened"

        updated = existing.model_copy(
            update={
                "status": status,
                "summary": candidate.summary,
                "recommended_action": candidate.recommended_action,
                "confidence": candidate.confidence,
                "last_detected_at": max(
                    existing.last_detected_at,
                    now,
                ),
                "occurrence_count": existing.occurrence_count + 1,
                "due_at": candidate.due_at,
                "flags": candidate.flags,
            }
        )

        self._repository.save_finding(updated)

        self._repository.add_event(
            FindingEvent(
                event_id=uuid4(),
                finding_id=existing.finding_id,
                event_type="detected_again",
                occurred_at=now,
                details=(
                    "Повторное обнаружение; "
                    f"новых оснований: {len(new_evidence_ids)}"
                ),
            )
        )

        if reopened:
            self._repository.add_event(
                FindingEvent(
                    event_id=uuid4(),
                    finding_id=existing.finding_id,
                    event_type="reopened",
                    occurred_at=now,
                    details=(
                        f"Карточка переоткрыта: "
                        f"добавлены основания {new_evidence_ids}"
                    ),
                )
            )

        return updated

    def change_status(
        self,
        finding_id: UUID,
        new_status: FindingStatus,
        occurred_at,
        comment: str,
    ) -> Finding:

        if not comment.strip():
            raise ValueError("Комментарий не должен быть пустым")

        with self._repository.transaction():
            existing = self._repository.find_by_id(finding_id)

            if existing is None:
                raise LookupError(f"Карточка не найдена: {finding_id}")

            allowed = {
                "open": {"acknowledged", "snoozed", "resolved", "rejected"},
                "reopened": {
                    "acknowledged", "snoozed", "resolved", "rejected"
                },
                "acknowledged": {"snoozed", "resolved", "rejected"},
                "snoozed": {"acknowledged", "resolved", "rejected"},
                "resolved": {"reopened"},
                "rejected": {"reopened"},
            }

            if new_status not in allowed.get(existing.status, set()):
                raise ValueError(
                    f"Недопустимый переход: "
                    f"{existing.status} -> {new_status}"
                )

            updated = existing.model_copy(
                update={"status": new_status}
            )
            self._repository.save_finding(updated)

            event_type = (
                "resolved"
                if new_status == "resolved"
                else "status_changed"
            )

            self._repository.add_event(
                FindingEvent(
                    event_id=uuid4(),
                    finding_id=finding_id,
                    event_type=event_type,
                    occurred_at=occurred_at,
                    details=(
                        f"{existing.status} -> {new_status}. "
                        f"{comment.strip()}"
                    ),
                )
            )

            return updated
