from responseflow_local.domain.models import ConversationWindow

from .semantic_analyzer import SemanticAnalyzer
from .semantic_models import AnalysisReport, SemanticResult
from .semantic_normalizer import (
    UnknownEvidenceError,
    validate_and_normalize,
)


class SemanticSituationService:
    def __init__(
        self,
        analyzer: SemanticAnalyzer,
        threshold: float = 0.60,
    ) -> None:
        self._analyzer = analyzer
        self._threshold = threshold

    def analyze(
        self,
        window: ConversationWindow,
    ) -> AnalysisReport:
        accepted: list[tuple[int, SemanticResult]] = []
        errors: list[str] = []
        below_threshold = 0
        invalid = 0

        available_ids = {
            message.external_id for message in window.messages
        }

        analyzed_results = self._analyzer.analyze(window)

        for index, result in enumerate(analyzed_results):
            if result.confidence < self._threshold:
                below_threshold += 1
                continue

            try:
                normalized = validate_and_normalize(
                    result,
                    available_ids,
                )
                accepted.append((index, normalized))
            except UnknownEvidenceError as error:
                invalid += 1
                errors.append(str(error))

        accepted.sort(
            key=lambda item: (-item[1].confidence, item[0])
        )

        return AnalysisReport(
            accepted=tuple(item[1] for item in accepted),
            below_threshold=below_threshold,
            invalid=invalid,
            errors=tuple(errors),
        )