from datetime import datetime, timedelta, timezone

from responseflow_local.application.analyze import AnalysisService
from responseflow_local.detectors.unanswered import UnansweredDetector


ANALYSIS_TIME = datetime(
    2026, 10, 17, 12, 0, tzinfo=timezone.utc
)


def test_analysis_saves_unanswered_finding(
    message_repository,
    finding_repository,
    finding_service,
    window_builder,
    message_revision_factory,
):
    messages = message_revision_factory(file_path='data/fixtures/messages.jsonl')
    message_repository.save_messages(messages)
    

    service = AnalysisService(
        message_repository=message_repository,
        finding_service=finding_service,
        window_builder=window_builder,
        detectors=(UnansweredDetector(),),
    )

    report = service.run("north", ANALYSIS_TIME)
    assert report.workspace_id == "north"
    assert report.analysis_time == ANALYSIS_TIME
    assert report.created_findings == 1
    assert report.updated_findings == 0

    findings = finding_repository.list_for_workspace("north")

    assert len(findings) == 1
    assert findings[0].type == "unanswered"
    assert findings[0].status == "open"

    evidence = finding_repository.list_evidence(
        findings[0].finding_id
    )

    assert len(evidence) == 1
    assert evidence[0].message_external_id == "n-006-002"