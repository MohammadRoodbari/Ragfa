"""
FastAPI dependency providers.

All heavy singletons (services, pipelines) live on ``app.state`` and are
injected into route handlers via these ``Depends()`` callables — never
imported directly in routers.

This keeps routes thin, makes mocking trivial in tests, and ensures the
expensive models are built exactly once at startup.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from backend.app.services.ingest_service import IngestService
from backend.app.services.query_service import QueryService

# ── Service accessors (sourced from app.state) ────────────────────────────────

def get_ingest_service(request: Request) -> IngestService:
    svc: IngestService | None = getattr(request.app.state, "ingest_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Ingest service not initialised")
    return svc


def get_query_service(request: Request) -> QueryService:
    svc: QueryService | None = getattr(request.app.state, "query_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Query service not initialised")
    return svc

# ── Typed dependency aliases ──────────────────
IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]
QueryServiceDep  = Annotated[QueryService,  Depends(get_query_service)]