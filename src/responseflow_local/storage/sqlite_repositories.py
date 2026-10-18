
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator
from uuid import UUID

from .sqlite import SqliteDatabase
from .models import Evidence, Finding, FindingEvent

class SqliteFindingRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database
        self._active_conn: sqlite3.Connection | None = None

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._active_conn is not None:
            raise RuntimeError("Вложенные транзакции не поддерживаются")

        with self._database.transaction() as conn:
            self._active_conn = conn
            try:
                yield
            finally:
                self._active_conn = None

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self._active_conn is not None:
            yield self._active_conn
        else:
            with self._database.connect() as conn:
                yield conn

    @staticmethod
    def _row_to_finding(row: sqlite3.Row) -> Finding:
        return Finding(
            finding_id=UUID(row["finding_id"]),
            workspace_id=row["workspace_id"],
            conversation_id=row["conversation_id"],
            project_id=row["project_id"],
            type=row["type"],
            subject_key=row["subject_key"],
            deduplication_key=row["deduplication_key"],
            status=row["status"],
            version=row["version"],
            summary=row["summary"],
            recommended_action=row["recommended_action"],
            confidence=row["confidence"],
            first_detected_at=datetime.fromisoformat(
                row["first_detected_at"]
            ),
            last_detected_at=datetime.fromisoformat(
                row["last_detected_at"]
            ),
            occurrence_count=row["occurrence_count"],
            due_at=(
                datetime.fromisoformat(row["due_at"])
                if row["due_at"] else None
            ),
            snoozed_until=(
                datetime.fromisoformat(row["snoozed_until"])
                if row["snoozed_until"] else None
            ),
        )

    def find_by_key(
        self, workspace_id: str, key: str
    ) -> Finding | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM findings
                WHERE workspace_id = ? AND deduplication_key = ?
                """,
                (workspace_id, key),
            ).fetchone()
            return self._row_to_finding(row) if row else None

    def find_by_id(self, finding_id: UUID) -> Finding | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM findings WHERE finding_id = ?",
                (str(finding_id),),
            ).fetchone()
            return self._row_to_finding(row) if row else None

    def list_for_workspace(
        self, workspace_id: str
    ) -> tuple[Finding, ...]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM findings
                WHERE workspace_id = ?
                ORDER BY first_detected_at, finding_id
                """,
                (workspace_id,),
            ).fetchall()
            return tuple(self._row_to_finding(row) for row in rows)

    
    def save_finding(self, finding: Finding) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO findings (
                    finding_id, workspace_id, conversation_id,
                    project_id, type, subject_key, deduplication_key,
                    status, version, summary, recommended_action,
                    confidence, first_detected_at, last_detected_at,
                    occurrence_count, due_at, snoozed_until
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(finding_id) DO UPDATE SET
                    status = excluded.status,
                    version = excluded.version,
                    summary = excluded.summary,
                    recommended_action = excluded.recommended_action,
                    confidence = excluded.confidence,
                    last_detected_at = excluded.last_detected_at,
                    occurrence_count = excluded.occurrence_count,
                    due_at = excluded.due_at,
                    snoozed_until = excluded.snoozed_until
                """,
                (
                    str(finding.finding_id),
                    finding.workspace_id,
                    finding.conversation_id,
                    finding.project_id,
                    finding.type,
                    finding.subject_key,
                    finding.deduplication_key,
                    finding.status,
                    finding.version,
                    finding.summary,
                    finding.recommended_action,
                    finding.confidence,
                    finding.first_detected_at.isoformat(),
                    finding.last_detected_at.isoformat(),
                    finding.occurrence_count,
                    finding.due_at.isoformat() if finding.due_at else None,
                    finding.snoozed_until.isoformat() if finding.snoozed_until else None,
                ),
            )


    def list_evidence(
        self, finding_id: UUID
    ) -> tuple[Evidence, ...]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT finding_id, message_external_id, added_at
                FROM evidence
                WHERE finding_id = ?
                ORDER BY added_at, message_external_id
                """,
                (str(finding_id),),
            ).fetchall()

            return tuple(
                Evidence(
                    finding_id=UUID(row["finding_id"]),
                    message_external_id=row["message_external_id"],
                    added_at=datetime.fromisoformat(row["added_at"]),
                )
                for row in rows
            )

    def add_evidence(self, evidence: Evidence) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence (
                    finding_id, message_external_id, added_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(finding_id, message_external_id) DO NOTHING
                """,
                (
                    str(evidence.finding_id),
                    evidence.message_external_id,
                    evidence.added_at.isoformat(),
                ),
            )

    def add_event(self, event: FindingEvent) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO finding_events (
                    event_id, finding_id, event_type, occurred_at, details
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    str(event.finding_id),
                    event.event_type,
                    event.occurred_at.isoformat(),
                    event.details,
                ),
            )

    def list_events(
        self, finding_id: UUID
    ) -> tuple[FindingEvent, ...]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT event_id, finding_id, event_type,
                       occurred_at, details
                FROM finding_events
                WHERE finding_id = ?
                ORDER BY occurred_at, event_id
                """,
                (str(finding_id),),
            ).fetchall()

            return tuple(
                sorted(
                    (
                        FindingEvent(
                            event_id=UUID(row["event_id"]),
                            finding_id=UUID(row["finding_id"]),
                            event_type=row["event_type"],
                            occurred_at=datetime.fromisoformat(row["occurred_at"]),
                            details=row["details"],
                        )
                        for row in rows
                    ),
                    key=lambda event: event.occurred_at,
                )
            )
