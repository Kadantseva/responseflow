import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    workspace_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    sender_id TEXT NOT NULL,
    sender_role TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    text TEXT NOT NULL,
    reply_to_external_id TEXT,
    source TEXT NOT NULL,
    PRIMARY KEY (workspace_id, external_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(workspace_id, conversation_id, sent_at);

CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    deduplication_key TEXT NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    summary TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    confidence REAL NOT NULL,
    first_detected_at TEXT NOT NULL,
    last_detected_at TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    due_at TEXT,
    snoozed_until TEXT,
    UNIQUE(workspace_id, deduplication_key)
);

CREATE TABLE IF NOT EXISTS evidence (
    finding_id TEXT NOT NULL,
    message_external_id TEXT NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (finding_id, message_external_id),
    FOREIGN KEY (finding_id) REFERENCES findings(finding_id)
);

CREATE TABLE IF NOT EXISTS finding_events (
    event_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    details TEXT NOT NULL,
    FOREIGN KEY (finding_id) REFERENCES findings(finding_id)
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    analysis_time TEXT NOT NULL,
    report_json TEXT NOT NULL
);
"""


class SqliteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()