"""
Structured request/response logging middleware.

Logs every request as a single JSON line with:
  - method, path, status_code
  - duration_ms
  - request_id (injected into request.state and response header)

Uses structlog for JSON output when LOG_LEVEL is INFO or lower.
"""
from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        t0 = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - t0) * 1000)

        log = logger.bind(
            request_id  = request_id,
            method      = request.method,
            path        = request.url.path,
            status_code = response.status_code,
            duration_ms = duration_ms,
            client_host = request.client.host if request.client else None,
        )

        if response.status_code >= 500:
            log.error("request_error")
        elif response.status_code >= 400:
            log.warning("request_warning")
        else:
            log.info("request_ok")

        response.headers["X-Request-Id"] = request_id
        return response