from datetime import datetime

from .completion_rules import (
    has_action_word,
    is_completion_text,
    is_unresolved_follow_up,
)
from .deadline_parser import parse_deadline
from .commitment_models import CommitmentCandidate, MessageView


class CommitmentDetector:
    version = "commitment-rules-1"

    def detect(
        self,
        conversation_id: str,
        messages: tuple[MessageView, ...],
        analysis_time: datetime,
    ) -> tuple[CommitmentCandidate, ...]:
        results: list[CommitmentCandidate] = []

        for index, message in enumerate(messages):
            if message.sender_role != "employee":
                continue

            if not has_action_word(message.text):
                continue

            due_at = parse_deadline(message.text, message.sent_at)
            if due_at is None:
                continue

            completion = self._find_completion(
                messages[index + 1:], analysis_time
            )
            if completion is not None:
                continue

            item_type = (
                "delay" if due_at <= analysis_time else "commitment"
            )

            follow_ups = self._find_unresolved_follow_ups(
                messages[index + 1:],
                message.external_id,
                analysis_time,
            )

            evidence_ids = (
                message.external_id,
                *(item.external_id for item in follow_ups),
            )

            results.append(
                CommitmentCandidate(
                    type=item_type,
                    subject_key=(
                        f"{item_type}:{conversation_id}:"
                        f"{message.external_id}"
                    ),
                    summary=message.text.strip()[:100],
                    due_at=due_at,
                    commitment_message_id=message.external_id,
                    completion_message_id=None,
                    evidence_message_ids=evidence_ids,
                    responsible_role="account_manager",
                )
            )

        return tuple(results)

    def _find_completion(
        self,
        later_messages: tuple[MessageView, ...],
        analysis_time: datetime,
    ) -> MessageView | None:
        for message in later_messages:
            if message.sent_at > analysis_time:
                continue

            if (
                message.sender_role == "employee"
                and is_completion_text(message.text)
            ):
                return message

        return None

    def _find_unresolved_follow_ups(
        self,
        later_messages: tuple[MessageView, ...],
        commitment_id: str,
        analysis_time: datetime,
    ) -> tuple[MessageView, ...]:
        return tuple(
            message
            for message in later_messages
            if message.sent_at <= analysis_time
            and message.sender_role == "customer"
            and message.reply_to_external_id == commitment_id
            and is_unresolved_follow_up(message.text)
        )