
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from responseflow_local.application.review import (
    AcknowledgeRequest,
    InboxService,
    RejectRequest,
    ResolveRequest,
    SnoozeRequest,
)


def create_router(service: InboxService) -> APIRouter:
    router = APIRouter(
        prefix="/workspaces/{workspace_id}/findings",
        tags=["findings"],
    )

    @router.get("/{finding_id}")
    def get_finding(workspace_id: str, finding_id: UUID):
        try:
            return jsonable_encoder(
                service.get_finding(workspace_id, finding_id).model_dump(
                    mode="json"
                )
            )
        except LookupError as error:
            raise HTTPException(404, str(error)) from error

    @router.get("/{finding_id}/history")
    def get_history(workspace_id: str, finding_id: UUID):
        try:
            events = service.get_history(workspace_id, finding_id)
            return jsonable_encoder(
                [event.model_dump(mode="json") for event in events]
            )
        except LookupError as error:
            raise HTTPException(404, str(error)) from error

    @router.post("/{finding_id}/acknowledge")
    def acknowledge(
        workspace_id: str,
        finding_id: UUID,
        command: AcknowledgeRequest,
    ):
        return execute(
            service.acknowledge, workspace_id, finding_id, command
        )

    @router.post("/{finding_id}/snooze")
    def snooze(
        workspace_id: str,
        finding_id: UUID,
        command: SnoozeRequest,
    ):
        return execute(service.snooze, workspace_id, finding_id, command)

    @router.post("/{finding_id}/resolve")
    def resolve(
        workspace_id: str,
        finding_id: UUID,
        command: ResolveRequest,
    ):
        return execute(service.resolve, workspace_id, finding_id, command)

    @router.post("/{finding_id}/reject")
    def reject(
        workspace_id: str,
        finding_id: UUID,
        command: RejectRequest,
    ):
        return execute(service.reject, workspace_id, finding_id, command)

    return router


def execute(operation, workspace_id, finding_id, command):
    try:
        result = operation(workspace_id, finding_id, command)
        return jsonable_encoder(result.model_dump(mode="json"))
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        from responseflow_local.application.review import (
            InvalidTransitionError,
            VersionConflictError,
        )

        if isinstance(error, (InvalidTransitionError, VersionConflictError)):
            raise HTTPException(409, str(error)) from error
        raise HTTPException(422, str(error)) from error
