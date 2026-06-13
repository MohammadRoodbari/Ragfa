from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import get_settings
from backend.app.core.redis_client import close_redis, get_redis
from backend.app.middleware.logging import LoggingMiddleware
from backend.app.routers import health, ingest, query
from backend.app.schemas.api import ErrorDetail
from backend.app.services.ingest_service import IngestService
from backend.app.services.query_service import QueryService

logger = structlog.get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(message)s",
    )
    logger.info("startup", env=settings.APP_ENV)

    # Verify Elasticsearch
    from  src.core.es_client import ping as ping_es
    if not ping_es():
        raise RuntimeError(
            "Cannot reach Elasticsearch at %s — check ES_HOST in .env" % settings.ES_HOST
        )

    # Warm up Redis pool
    await get_redis()

    # Build services (heavy models loaded once here)
    app.state.ingest_service = IngestService()
    app.state.query_service  = QueryService()

    logger.info("all_services_ready")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    await close_redis()
    logger.info("shutdown_complete")


# ── Exception handlers ────────────────────────────────────────────────────────

async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorDetail(
            code="internal_error",
            message="An unexpected error occurred.",
        ).model_dump(),
    )


async def _http_exception_handler(request: Request, exc) -> JSONResponse:  # type: ignore[override]
    from fastapi.exceptions import HTTPException
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorDetail(
            code="http_error",
            message=exc.detail,
        ).model_dump(),
    )


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title       = "Documents RAG API",
        description = (
            "Hybrid kNN + BM25 retrieval with LLM-powered generation. "
            "Supports multi-turn conversation via Redis-backed session history."
        ),
        version     = "1.0.0",
        lifespan    = lifespan,
        docs_url    = "/docs"   if settings.APP_ENV != "production" else None,
        redoc_url   = "/redoc"  if settings.APP_ENV != "production" else None,
        openapi_url = "/openapi.json" if settings.APP_ENV != "production" else None,
    )

    # ── Middleware (order matters: outermost = first to run) ──────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["*"] if settings.APP_ENV == "development" else [],
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )
    app.add_middleware(LoggingMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    from fastapi.exceptions import HTTPException
    app.add_exception_handler(HTTPException,  _http_exception_handler)
    app.add_exception_handler(Exception,      _unhandled_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(ingest.router, prefix="/api/v1")
    app.include_router(query.router,  prefix="/api/v1")

    return app


# Module-level app instance used by uvicorn / gunicorn
app = create_app()