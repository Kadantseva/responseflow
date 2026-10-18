from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from responseflow_local.application.review import (
    FindingNotFoundError,
    InvalidTransitionError,
    VersionConflictError,
)
from responseflow_local.container import build_application
from .routes import create_router


def create_app(database_path: Path) -> FastAPI:
    container = build_application(database_path, Path("data/fixtures"))
    app = FastAPI(title="ResponseFlow Local")
    app.include_router(create_router(container.inbox_service))

    @app.exception_handler(FindingNotFoundError)
    async def not_found(request, exc):
        return JSONResponse(404, {"detail": str(exc)})

    @app.exception_handler(InvalidTransitionError)
    async def invalid_transition(request, exc):
        return JSONResponse(409, {"detail": str(exc)})

    @app.exception_handler(VersionConflictError)
    async def version_conflict(request, exc):
        return JSONResponse(409, {"detail": str(exc)})

    return app