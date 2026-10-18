from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from responseflow_local.domain.catalog import Catalog
from responseflow_local.domain.models import MessageRevision
from responseflow_local.domain.models import Participant, Project
from responseflow_local.domain.window_builder import WindowBuilder
from responseflow_local.storage.sqlite_message_repository import SqliteMessageRepository
from responseflow_local.storage.sqlite_repositories import SqliteFindingRepository
from responseflow_local.storage.sqlite import SqliteDatabase
from responseflow_local.application.finding_service import FindingService
from responseflow_local.application.review import InboxService


@pytest.fixture
def database(tmp_path):
    """Изолированная SQLite-база для каждого теста."""
    db = SqliteDatabase(tmp_path / "test.sqlite3")
    db.initialize()
    return db

@pytest.fixture
def participants():
    file_path = Path("data") / "fixtures" / "participants.json"

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return tuple(Participant(**item) for item in data)

@pytest.fixture
def inbox_service(finding_repository):
    return InboxService(finding_repository)

@pytest.fixture
def projects():
    file_path = Path("data") / "fixtures" / "projects.json"

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return tuple(Project(**item) for item in data)


@pytest.fixture
def catalog(participants, projects):
    return Catalog(
        participants=participants,
        projects=projects,
    )


@pytest.fixture
def window_builder(catalog):
    return WindowBuilder(catalog)

@pytest.fixture
def message_repository(database):
    return SqliteMessageRepository(database)


@pytest.fixture
def finding_repository(database):
    return SqliteFindingRepository(database)


@pytest.fixture
def finding_service(finding_repository):
    return FindingService(finding_repository)


@pytest.fixture
def message_revision_factory():
    """Читает сообщения из JSONL и возвращает список MessageRevision."""

    def load(file_path: str | Path) -> list[MessageRevision]:
        messages = []

        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                data = json.loads(line)
                data["sent_at"] = datetime.fromisoformat(data["sent_at"])
                data["observed_at"] = datetime.fromisoformat(
                    data["observed_at"]
                )

                messages.append(MessageRevision(**data))

        return messages

    return load
