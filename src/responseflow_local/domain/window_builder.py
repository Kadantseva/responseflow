from collections.abc import Iterable
from datetime import datetime
from itertools import groupby

from .catalog import Catalog
from .models import ConversationWindow, MessageView
from .models import MessageRevision


def select_latest_known_revisions(
    messages: Iterable[MessageRevision], analysis_time: datetime
) -> tuple[MessageRevision, ...]:
    latest_by_external_id: dict[str, MessageRevision] = {}

    for msg in messages:
        if msg.observed_at is None or msg.observed_at > analysis_time:
            continue

        current = latest_by_external_id.get(msg.external_id)
        if current is None or msg.revision > current.revision:
            latest_by_external_id[msg.external_id] = msg

    return tuple(latest_by_external_id.values())


def sort_messages(messages: Iterable[MessageRevision]) -> tuple[MessageRevision, ...]:
    return tuple(sorted(
        messages,
        key=lambda item: (item.sent_at, item.external_id, item.revision),
    ))


class WindowBuilder:
    def __init__(self, catalog: Catalog, limit: int = 12) -> None:
        self._catalog = catalog
        self._limit = limit

    def build(self, workspace_id: str, conversation_id: str,
              messages: Iterable[MessageRevision],
              analysis_time: datetime) -> ConversationWindow:

        filtered_by_context = [
            msg for msg in messages
            if msg.workspace_id == workspace_id and msg.conversation_id == conversation_id
        ]
        
        omitted_before = 0
        
        if not filtered_by_context:
            project = self._catalog.project_for_conversation(workspace_id, conversation_id)
            return ConversationWindow(                
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                project_id=project.project_id,
                analysis_time=analysis_time,
                messages=(),
                omitted_before=omitted_before,
                response_sla_minutes=0
            )

        project = self._catalog.project_for_conversation(workspace_id, conversation_id)

        latest_revisions = select_latest_known_revisions(filtered_by_context, analysis_time)

        past_messages = [
            msg for msg in latest_revisions
            if msg.sent_at is not None and msg.sent_at <= analysis_time
        ]

        sorted_messages = sorted(past_messages, key=lambda m: m.sent_at or datetime.min)

        is_truncated = len(sorted_messages) > self._limit
        total_count = len(sorted_messages)
        omitted_before = max(0, total_count - self._limit) if is_truncated else 0
        limited_messages = sorted_messages[-self._limit:] if is_truncated else sorted_messages
        messages_to_convert = list(limited_messages)
        
        for msg in limited_messages:
            if msg.reply_to_external_id is None:
                continue
            
            parent = next(
                (m for m in past_messages if m.external_id == msg.reply_to_external_id),
                None
            )
            
            if parent and parent not in messages_to_convert:
                messages_to_convert.insert(0, parent)

        view_messages: list[MessageView] = []
        for msg in messages_to_convert:
            view = self._to_view(workspace_id, msg)
            view_messages.append(view)

        return ConversationWindow(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            project_id=project.project_id,
            analysis_time=analysis_time,
            messages=tuple(view_messages),
            omitted_before=omitted_before,
            response_sla_minutes=project.response_sla_minutes
        )

    def _to_view(self, workspace_id: str,
                 message: MessageRevision) -> MessageView:
        participant = self._catalog.participant(workspace_id, message.sender_id)
        return MessageView(
            external_id=message.external_id,
            revision=message.revision,
            sender_role=message.sender_role,
            sender_name=participant.display_name,
            sent_at=message.sent_at,
            text=message.text,
            reply_to_external_id=message.reply_to_external_id,
        )