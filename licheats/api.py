from __future__ import annotations

import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .app import Licheats
from .lichess import LichessError
from .schemas import ErrorDetail, ErrorResponse, PlayerAnalysis, PlayerProfileSummary, SyncJobStatus, SyncResult
from .settings import Settings

logger = logging.getLogger(__name__)


def _error_response(code: str, message: str, status_code: int, details: dict[str, Any] | None = None) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details or {}))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def create_app(settings: Settings | None = None, service: Licheats | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    service = service or Licheats(settings)
    app = FastAPI(title="Licheats API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(LichessError)
    async def handle_lichess_error(_request, exc: LichessError) -> JSONResponse:
        upstream_status = exc.details.get("status_code")
        status_code = 404 if upstream_status == 404 else 502
        return _error_response(exc.code, str(exc), status_code, exc.details)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled Licheats API error", exc_info=exc)
        return _error_response("internal_error", "Unexpected internal error.", 500)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/players/{username}/analysis", response_model=PlayerAnalysis)
    def analyze_player(
        username: str,
        limit: int = Query(default=100, ge=1, le=5000),
        refresh: bool = False,
        perf_type: str | None = None,
    ) -> PlayerAnalysis:
        return service.analyze_player(username, limit=limit, refresh=refresh, perf_type=perf_type)

    @app.get("/players/{username}/profile-summary", response_model=PlayerProfileSummary)
    def profile_summary(username: str) -> PlayerProfileSummary:
        return service.profile_summary(username)

    @app.post("/players/{username}/sync", response_model=SyncResult)
    def sync_player(
        username: str,
        limit: int = Query(default=100, ge=1, le=1000),
        perf_type: str | None = None,
        include_moves: bool = True,
        page_size: int = Query(default=1000, ge=1, le=1000),
    ) -> SyncResult:
        return service.sync_player(
            username,
            limit=limit,
            perf_type=perf_type,
            include_moves=include_moves,
            page_size=page_size,
        )

    @app.post("/players/{username}/sync-jobs", response_model=SyncJobStatus)
    def start_sync_job(
        username: str,
        limit: int = Query(default=5000, ge=1, le=20000),
        perf_type: str | None = None,
        include_moves: bool = False,
        page_size: int = Query(default=1000, ge=1, le=5000),
    ) -> SyncJobStatus:
        return service.start_sync_job(
            username,
            limit=limit,
            perf_type=perf_type,
            include_moves=include_moves,
            page_size=page_size,
        )

    @app.get("/sync-jobs/{job_id}", response_model=SyncJobStatus)
    def sync_job_status(job_id: str) -> SyncJobStatus:
        job = service.get_sync_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Sync job not found")
        return job

    return app


def main() -> None:
    uvicorn.run("licheats.api:create_app", factory=True, host="127.0.0.1", port=8000, reload=False)
