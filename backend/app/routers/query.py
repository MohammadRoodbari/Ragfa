"""
Query router — /query/*

Endpoints
---------
POST /query         — blocking: full answer + attributed sources
POST /query/stream  — streaming: SSE token-by-token, session_id echoed in header
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.app.dependencies import QueryServiceDep
from backend.app.schemas.api import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


# ── POST /query ───────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=QueryResponse,
    summary="Ask a question — full blocking response",
    description=(
        "Retrieves relevant document chunks and generates a complete answer. "
        "Pass a `session_id` to enable multi-turn conversation: the LLM will "
        "see previous turns stored in Redis."
    ),
)
async def query(
    svc: QueryServiceDep,
    request: QueryRequest,
) -> QueryResponse:
    try:
        return await svc.query(request)
    except Exception as exc:
        logger.exception("query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query failed. Check server logs for details.",
        ) from exc


# ── POST /query/stream ────────────────────────────────────────────────────────

@router.post(
    "/stream",
    summary="Ask a question — streaming token response (SSE)",
    description=(
        "Streams the LLM answer token-by-token using Server-Sent Events. "
        "Each event is a plain text chunk.  The stream ends with a sentinel "
        "line `data: [DONE]\\n\\n`.  "
        "Sources are **not** included in the stream — use POST /query for those. "
        "Pass `session_id` in the request body for conversation memory."
    ),
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Stream of SSE events containing answer tokens.",
        }
    },
)
async def query_stream(
    svc: QueryServiceDep,
    request: QueryRequest,
) -> StreamingResponse:
    async def _event_generator():
        try:
            async for token in svc.stream(request):
                yield f"data: {token}\n\n"
        except Exception as exc:
            logger.exception("stream failed: %s", exc)
            yield "data: [ERROR]\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            # Disable buffering in nginx / proxy layers
            "X-Accel-Buffering":    "no",
            "Cache-Control":        "no-cache",
            # Echo session_id so the client can store it from a single header
            "X-Session-Id":         request.session_id or "",
        },
    )