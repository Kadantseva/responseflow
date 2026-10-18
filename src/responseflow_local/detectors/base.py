from typing import Protocol

from responseflow_local.domain.findings import FindingCandidate
from responseflow_local.domain.models import ConversationWindow


class SituationDetector(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def detect(self, window: ConversationWindow) -> tuple[FindingCandidate, ...]: ...