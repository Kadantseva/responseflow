
from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from responseflow_local.storage.models import Finding
from responseflow_local.storage.sqlite_repositories import SqliteFindingRepository


class TypeSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    finding_type: str
    total: int = Field(ge=0)
    open: int = Field(ge=0)
    acknowledged: int = Field(ge=0)
    snoozed: int = Field(ge=0)
    resolved: int = Field(ge=0)
    rejected: int = Field(ge=0)
    reopened: int = Field(ge=0)


class ReportSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: str
    total: int = Field(ge=0)
    by_status: dict[str, int]
    by_type: tuple[TypeSummary, ...]
    active: int = Field(ge=0)
    resolved: int = Field(ge=0)
    rejected: int = Field(ge=0)


class ReportService:
    def __init__(self, repository: SqliteFindingRepository) -> None:
        self._repository = repository

    def build(self, workspace_id: str) -> ReportSummary:
        findings: tuple[Finding, ...] = (
            self._repository.list_for_workspace(workspace_id)
        )

        status_counts = Counter(item.status for item in findings)
        type_groups: dict[str, list[Finding]] = {}

        for item in findings:
            type_groups.setdefault(item.type, []).append(item)

        by_type = tuple(
            TypeSummary(
                finding_type=finding_type,
                total=len(items),
                open=sum(item.status == "open" for item in items),
                acknowledged=sum(
                    item.status == "acknowledged" for item in items
                ),
                snoozed=sum(item.status == "snoozed" for item in items),
                resolved=sum(item.status == "resolved" for item in items),
                rejected=sum(item.status == "rejected" for item in items),
                reopened=sum(item.status == "reopened" for item in items),
            )
            for finding_type, items in sorted(type_groups.items())
        )

        active_statuses = {"open", "acknowledged", "snoozed", "reopened"}

        return ReportSummary(
            workspace_id=workspace_id,
            total=len(findings),
            by_status=dict(sorted(status_counts.items())),
            by_type=by_type,
            active=sum(item.status in active_statuses for item in findings),
            resolved=status_counts["resolved"],
            rejected=status_counts["rejected"],
        )

    def list_findings(self, workspace_id: str) -> tuple[Finding, ...]:
        return self._repository.list_for_workspace(workspace_id)
