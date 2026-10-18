
from datetime import datetime

from responseflow_local.domain.models import MessageRevision
from responseflow_local.domain.models import MessageView


class SqliteMessageRepository:
    def __init__(self, database) -> None:
        self._database = database

    def save_messages(
        self,
        messages: tuple[MessageRevision, ...],
    ) -> int:
        """Сохранить новые ревизии сообщений, не создавая дубликатов."""
        inserted = 0

        with self._database.transaction() as conn:
            for message in messages:
                cursor = conn.execute(
                    """
                    INSERT INTO messages (
                        workspace_id, conversation_id, external_id,
                        revision, sender_id, sender_role, sent_at,
                        observed_at, text, reply_to_external_id, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(workspace_id, external_id, revision)
                    DO NOTHING
                    """,
                    (
                        message.workspace_id,
                        message.conversation_id,
                        message.external_id,
                        message.revision,
                        message.sender_id,
                        message.sender_role,
                        message.sent_at.isoformat(),
                        message.observed_at.isoformat(),
                        message.text,
                        message.reply_to_external_id,
                        message.source,
                    ),
                )
                inserted += cursor.rowcount

        return inserted

    def list_conversations(self, workspace_id: str) -> tuple[str, ...]:
        with self._database.connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT conversation_id
                FROM messages
                WHERE workspace_id = ?
                ORDER BY conversation_id
                """,
                (workspace_id,),
            ).fetchall()

        return tuple(row["conversation_id"] for row in rows)

    
    def get_window_messages(
        self,
        workspace_id: str,
        conversation_id: str,
        analysis_time: datetime,
    ) -> tuple[MessageRevision, ...]:
        """Получить последние известные ревизии сообщений на момент анализа."""
        analysis_time_iso = analysis_time.isoformat()

        with self._database.connect() as conn:
            rows = conn.execute(
                """
                SELECT m.*
                FROM messages AS m
                JOIN (
                    SELECT
                        workspace_id,
                        external_id,
                        MAX(revision) AS revision
                    FROM messages
                    WHERE workspace_id = ?
                    AND conversation_id = ?
                    AND observed_at <= ?
                    GROUP BY workspace_id, external_id
                ) AS latest
                ON latest.workspace_id = m.workspace_id
                AND latest.external_id = m.external_id
                AND latest.revision = m.revision
                WHERE m.workspace_id = ?
                AND m.conversation_id = ?
                AND m.sent_at <= ?
                ORDER BY m.sent_at, m.external_id
                """,
                (
                    workspace_id,
                    conversation_id,
                    analysis_time_iso,
                    workspace_id,
                    conversation_id,
                    analysis_time_iso,
                ),
            ).fetchall()

        return tuple(
            MessageRevision(
                workspace_id=row["workspace_id"],
                conversation_id=row["conversation_id"],
                external_id=row["external_id"],
                revision=row["revision"],
                sender_id=row["sender_id"],
                sender_role=row["sender_role"],
                sent_at=datetime.fromisoformat(row["sent_at"]),
                observed_at=datetime.fromisoformat(row["observed_at"]),
                text=row["text"],
                reply_to_external_id=row["reply_to_external_id"],
                source=row["source"],
            )
            for row in rows
        )

