from typing import Protocol

from responseflow_local.domain.models import ConversationWindow
from .semantic_models import SemanticResult


class SemanticAnalyzer(Protocol):
    def analyze(
        self,
        window: ConversationWindow,
    ) -> tuple[SemanticResult, ...]: ...