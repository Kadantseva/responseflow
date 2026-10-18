
from contextlib import AbstractContextManager
from typing import Protocol
from uuid import UUID

from .models import Evidence, Finding, FindingEvent


class FindingRepository(Protocol):
    def transaction(self) -> AbstractContextManager[None]: ...

    def find_by_key(
        self, workspace_id: str, key: str
    ) -> Finding | None: ...

    def find_by_id(self, finding_id: UUID) -> Finding | None: ...

    def save_finding(self, finding: Finding) -> None: ...

    def list_evidence(
        self, finding_id: UUID
    ) -> tuple[Evidence, ...]: ...

    def add_evidence(self, evidence: Evidence) -> None: ...

    def add_event(self, event: FindingEvent) -> None: ...

    def list_events(
        self, finding_id: UUID
    ) -> tuple[FindingEvent, ...]: ...

    def list_for_workspace(
        self, workspace_id: str
    ) -> tuple[Finding, ...]: ...