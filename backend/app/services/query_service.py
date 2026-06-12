"""
QueryService — orchestrates retrieval + generation with conversation memory.

Flow
----
1. Load conversation history from Redis (keyed by session_id).
2. Build a ``RAGRequest`` that includes history so the LLM sees context.
3. Call ``RAGPipeline.run()`` or ``RAGPipeline.stream()``.
4. Persist the new user turn + assistant answer back to Redis.
5. Return a typed ``QueryResponse`` (or an async generator for streaming).

The service is instantiated once and held on ``app.state`` via FastAPI's
dependency injection — see ``app/dependencies.py``.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncGenerator

from backend.app.core.config import get_settings
from backend.app.core.redis_client import append_conversation, get_conversation
from backend.app.schemas.api import QueryRequest, QueryResponse, SourceDocument

logger = logging.getLogger(__name__)


class QueryService:
    def __init__(self) -> None:
        self._settings = get_settings()
        from src.rag.pipeline import RAGPipeline
        self._pipeline: RAGPipeline = RAGPipeline.build()
        logger.info("QueryService ready (model=%s)", self._settings.LLM_MODEL)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _load_history(self, session_id: str | None) -> list[dict[str, str]]:
        if session_id is None:
            return []
        return await get_conversation(session_id)

    async def _save_turn(
        self,
        session_id: str | None,
        question: str,
        answer: str,
    ) -> None:
        if session_id is None:
            return
        await append_conversation(session_id, role="user",      content=question)
        await append_conversation(session_id, role="assistant", content=answer)

    @staticmethod
    def _map_sources(raw_sources: list) -> list[SourceDocument]:
        """Convert internal pipeline source objects to API schema."""
        out: list[SourceDocument] = []
        for s in raw_sources:
            out.append(
                SourceDocument(
                    source    = getattr(s, "source",    ""),
                    text      = getattr(s, "text",      ""),
                )
            )
        return out

    # ── Public API ────────────────────────────────────────────────────────────

    async def query(self, request: QueryRequest) -> QueryResponse:
        """
        Full blocking query: retrieve → generate → return complete response.

        Parameters
        ----------
        request: QueryRequest
            Validated API request including question and optional session_id.

        Returns
        -------
        QueryResponse
            Answer text, attributed sources, session ID, and latency.
        """
        from src.rag.schema import RAGRequest

        history = await self._load_history(request.session_id)
        t0 = time.perf_counter()

        rag_request = RAGRequest(
            question   = request.question,
            history    = history,
        )

        rag_response = await asyncio.get_event_loop().run_in_executor(
            None,
            self._pipeline.run,
            rag_request,
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)

        await self._save_turn(
            request.session_id,
            request.question,
            rag_response.answer,
        )

        return QueryResponse(
            answer     = rag_response.answer,
            sources    = self._map_sources(getattr(rag_response, "sources", [])),
            session_id = request.session_id,
            model      = getattr(rag_response, "model", self._settings.LLM_MODEL),
            latency_ms = latency_ms,
        )

    async def stream(self, request: QueryRequest) -> AsyncGenerator[str, None]:
        """
        Streaming query: yield answer tokens one by one as they arrive.

        The conversation turn is saved *after* the full answer has been
        accumulated from the stream so we store the complete assistant message.

        Yields
        ------
        str
            Individual tokens / text chunks from the LLM.
        """
        from src.rag.schema import RAGRequest

        history = await self._load_history(request.session_id)

        rag_request = RAGRequest(
            question  = request.question,
            history   = history,
        )

        accumulated: list[str] = []

        loop = asyncio.get_event_loop()
        sync_gen = self._pipeline.stream(rag_request)

        # Wrap synchronous generator as async
        def _next():
            try:
                return next(sync_gen)
            except StopIteration:
                return None

        while True:
            token = await loop.run_in_executor(None, _next)
            if token is None:
                break
            accumulated.append(token)
            yield token

        # Persist the full conversation turn once streaming is done
        await self._save_turn(
            request.session_id,
            request.question,
            "".join(accumulated),
        )