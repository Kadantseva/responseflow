from responseflow_local.detectors.base import SituationDetector
from responseflow_local.domain.findings import FindingCandidate
from responseflow_local.domain.catalog import Catalog
from responseflow_local.domain.models import ConversationWindow
from responseflow_local.llm.analyzer import LlmSituationAnalyzer


class LlmSituationDetector:
    name = "llm_situations"
    version = "llm-situations-1"

    def __init__(
        self,
        analyzer: LlmSituationAnalyzer,
        catalog: Catalog,
    ) -> None:
        self._analyzer = analyzer
        self._catalog = catalog

    def detect(
        self,
        window: ConversationWindow,
    ) -> tuple[FindingCandidate, ...]:
        project = self._catalog.project_for_conversation(
            window.workspace_id,
            window.conversation_id,
        )

        project_context = (
            f"Проект: {project.project_name}. "
            f"Организация: {project.organization_name}. "
            f"Тариф: {project.service_tier}. "
            f"Ответственная роль: {project.responsible_role}. "
            f"SLA ответа: {project.response_sla_minutes} минут."
        )

        result = self._analyzer.analyze(
            window=window,
            project_context=project_context,
        )

        candidates = []

        for situation in result.situations:
            candidates.append(
                FindingCandidate(
                    workspace_id=window.workspace_id,
                    conversation_id=window.conversation_id,
                    project_id=window.project_id,
                    type=situation.type,
                    confidence=situation.confidence,
                    subject_key=situation.subject_key,
                    summary=situation.summary,
                    recommended_action=situation.recommended_action,
                    evidence_message_ids=situation.evidence_message_ids,
                    detected_at=window.analysis_time,
                    due_at=None,
                    waiting_minutes=0,
                    flags=(),
                )
            )

        return tuple(candidates)