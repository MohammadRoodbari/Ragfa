"""
Health router — GET /health

Returns liveness status for every upstream dependency.
Used by load balancers, Docker HEALTHCHECK, and monitoring dashboards.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.core.redis_client import ping_redis
from backend.app.schemas.api import HealthResponse

router = APIRouter(tags=["ops"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Returns HTTP 200 when all dependencies are reachable, 503 otherwise.",
)
async def health() -> JSONResponse:
    from src.core.es_client import ping as ping_es

    es_ok    = ping_es()
    redis_ok = await ping_redis()
    all_ok   = es_ok and redis_ok

    payload = HealthResponse(
        status        = "ok" if all_ok else "degraded",
        elasticsearch = es_ok,
        redis         = redis_ok,
    )

    return JSONResponse(
        content    = payload.model_dump(),
        status_code = 200 if all_ok else 503,
    )