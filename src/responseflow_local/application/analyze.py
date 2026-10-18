from datetime import datetime, timezone
from uuid import uuid4

from responseflow_local.domain.findings import AnalysisRunReport, DetectorRun
from responseflow_local.detectors.base import SituationDetector


def safe_detector_error(error: Exception) -> str:
    """Не включать в отчёт запрос, ответ модели, ключи и стек вызовов."""
    return f"{type(error).__name__}: анализатор не завершил обработку"


class AnalysisService:
    def __init__(
        self,
        message_repository,
        finding_service,
        window_builder,
        detectors: tuple[SituationDetector, ...],
    ) -> None:
        self._messages = message_repository
        self._findings = finding_service
        self._window_builder = window_builder
        self._detectors = detectors

    def run(
        self,
        workspace_id: str,
        analysis_time: datetime,
    ) -> AnalysisRunReport:
        if (
            analysis_time.tzinfo is None
            or analysis_time.utcoffset() is None
        ):
            raise ValueError("analysis_time должен содержать часовой пояс")

        detector_runs: list[DetectorRun] = []
        created = 0
        updated = 0

        for conversation_id in self._messages.list_conversations(
            workspace_id
        ):
            messages = self._messages.get_window_messages(
                workspace_id,
                conversation_id,
                analysis_time,
            )
            
            window = self._window_builder.build(
                workspace_id,
                conversation_id,
                messages,
                analysis_time,
            )
            for detector in self._detectors:
                try:
                    candidates = detector.detect(window)

                    for candidate in candidates:
                        if (
                            candidate.workspace_id != workspace_id
                            or candidate.conversation_id != conversation_id
                        ):
                            raise ValueError(
                                "Кандидат относится к другой беседе"
                            )

                        finding = self._findings.record(candidate)
  

                        if finding.occurrence_count == 1:
                            created += 1
                        else:
                            updated += 1

                    detector_runs.append(
                        DetectorRun(
                            detector_name=detector.name,
                            detector_version=detector.version,
                            status="succeeded",
                            candidate_count=len(candidates),
                        )
                    )

                except Exception as error:
                    detector_runs.append(
                        DetectorRun(
                            detector_name=detector.name,
                            detector_version=detector.version,
                            status="failed",
                            candidate_count=0,
                            error=safe_detector_error(error),
                        )
                    )

        report = AnalysisRunReport(
            run_id=uuid4(),
            workspace_id=workspace_id,
            analysis_time=analysis_time,
            created_findings=created,
            updated_findings=updated,
            detector_runs=tuple(detector_runs),
        )

        return report
