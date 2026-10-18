
import json
from pathlib import Path

import pytest


MESSAGES_FILE = "data/fixtures/messages.jsonl"


def test_import_messages_creates_records(
    message_repository,
    message_revision_factory,
):
    messages = message_revision_factory(file_path=MESSAGES_FILE)

    message_repository.save_messages(messages)

    conversations = message_repository.list_conversations("north")

    assert conversations


def test_reimport_does_not_duplicate_messages(
    message_repository,
    message_revision_factory,
):
    messages = message_revision_factory(file_path=MESSAGES_FILE)

    message_repository.save_messages(messages)
    message_repository.save_messages(messages)

    conversations = message_repository.list_conversations("north")

    assert conversations


def test_import_rejects_invalid_jsonl(
    message_revision_factory,
    tmp_path: Path,
):
    path = tmp_path / "invalid.jsonl"
    path.write_text(
        '{"workspace_id": "north"}\n'
        "this is not json\n",
        encoding="utf-8",
    )

    with pytest.raises((ValueError, Exception)):
        message_revision_factory(file_path=str(path))


def test_import_preserves_message_revisions(
    message_repository,
    message_revision_factory,
    tmp_path: Path,
):
    messages = message_revision_factory(file_path=MESSAGES_FILE)
    message_repository.save_messages(messages)

    revision = {
        "workspace_id": "north",
        "conversation_id": "conversation-1",
        "external_id": "n-006-002",
        "revision": 2,
        "sender_id": "customer-1",
        "sender_role": "customer",
        "sent_at": "2026-10-15T10:00:00+03:00",
        "observed_at": "2026-10-15T10:10:00+03:00",
        "text": "Подскажите, когда будет готов обновлённый отчёт?",
        "reply_to_external_id": None,
        "source": "telegram",
    }

    revision_file = tmp_path / "revision.jsonl"
    revision_file.write_text(
        json.dumps(revision, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    revision_messages = message_revision_factory(
        file_path=str(revision_file)
    )
    message_repository.save_messages(revision_messages)

    with message_repository._database.connect() as conn:
        rows = conn.execute(
            """
            SELECT revision
            FROM messages
            WHERE workspace_id = ?
              AND external_id = ?
            ORDER BY revision
            """,
            ("north", "n-006-002"),
        ).fetchall()

    assert [row["revision"] for row in rows] == [1, 2]
