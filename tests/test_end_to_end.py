
from datetime import datetime, timezone
from pathlib import Path

import pytest

from responseflow_local.application.analyze import AnalysisService
from responseflow_local.application.review import (
    AcknowledgeRequest,
    VersionConflictError,
)
from responseflow_local.detectors.unanswered import UnansweredDetector
from responseflow_local.storage.sqlite import SqliteDatabase


NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
MESSAGES_FILE = "data/fixtures/messages.jsonl"


@pytest.fixture
def analysis_service(
    message_repository,
    finding_service,
    window_builder,
):
    return AnalysisService(
        message_repository=message_repository,
        finding_service=finding_service,
        window_builder=window_builder,
        detectors=(UnansweredDetector(),),
    )


@pytest.fixture
def prepared_analysis(
    message_repository,
    message_revision_factory,
    analysis_service,
):
    messages = message_revision_factory(file_path=MESSAGES_FILE)
    message_repository.save_messages(messages)

    report = analysis_service.run("north", NOW)

    return report


def test_end_to_end_import_analyze_and_acknowledge(
    prepared_analysis,
    finding_repository,
    inbox_service,
):
    report = prepared_analysis

    assert report.workspace_id == "north"
    assert report.analysis_time == NOW
    assert report.created_findings == 1
    assert report.updated_findings == 0

    findings = finding_repository.list_for_workspace("north")

    assert len(findings) == 1

    finding = findings[0]

    assert finding.workspace_id == "north"
    assert finding.type == "unanswered"
    assert finding.status == "open"
    assert finding.version == 1

    detail = inbox_service.get_finding(
        workspace_id="north",
        finding_id=finding.finding_id,
    )

    assert detail.finding_id == finding.finding_id
    assert detail.subject_key == finding.subject_key

    command = AcknowledgeRequest(
        author="test-manager",
        expected_version=detail.version,
        occurred_at=NOW,
        comment="Проверено интеграционным тестом",
    )

    acknowledged = inbox_service.acknowledge(
        workspace_id="north",
        finding_id=finding.finding_id,
        command=command,
    )

    assert acknowledged.status == "acknowledged"
    assert acknowledged.version == detail.version + 1

    history = inbox_service.get_history(
        workspace_id="north",
        finding_id=finding.finding_id,
    )

    assert len(history) == 2


def test_end_to_end_rejects_stale_manager_decision(
    prepared_analysis,
    finding_repository,
    inbox_service,
):
    findings = finding_repository.list_for_workspace("north")

    assert len(findings) == 1

    finding = findings[0]

    command = AcknowledgeRequest(
        author="test-manager",
        expected_version=finding.version,
        occurred_at=NOW,
        comment="Принимаю в работу",
    )

    inbox_service.acknowledge(
        workspace_id="north",
        finding_id=finding.finding_id,
        command=command,
    )

    with pytest.raises(VersionConflictError):
        inbox_service.acknowledge(
            workspace_id="north",
            finding_id=finding.finding_id,
            command=command,
        )


def test_end_to_end_data_survives_reopening_database(
    tmp_path: Path,
):
    database_path = tmp_path / "persistent.db"

    first_database = SqliteDatabase(database_path)
    first_database.initialize()
    first_database.initialize()

    with first_database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert {
        "messages",
        "findings",
        "evidence",
        "finding_events",
        "analysis_runs",
    } <= tables

    second_database = SqliteDatabase(database_path)
    second_database.initialize()

    with second_database.connect() as connection:
        persisted_tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert persisted_tables == tables
