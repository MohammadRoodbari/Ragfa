from __future__ import annotations

from typing import Generator

from config.settings import get_settings
from src.rag.llm.base import BaseLLMClient
from src.rag.llm.factory import create_llm_client
from src.rag.query_condenser import QueryCondenser       
from src.rag.schema import RAGRequest, RAGResponse, SourceDoc
from src.retrieval.pipeline import RetrievalPipeline

import structlog
logger = structlog.get_logger(__name__)

settings = get_settings()


class RAGPipeline:
    """
    Top-level entry point for the RAG phase.

    Wires together:
        RAGRequest
          → QueryCondenser   (history-aware query rewriting)   ← NEW
          → RetrievalPipeline (embed → hybrid search → RRF → context build)
          → LLMClient         (prompt → llm client → answer)
          → RAGResponse       (answer + attributed sources)

    Typical usage
    -------------
    >>> pipeline = RAGPipeline.build()
    >>> response = pipeline.run(
    ...     RAGRequest(
    ...         question="What were Q3 revenues?",
    ...         history=[
    ...             {"role": "user",      "content": "Tell me about the annual report."},
    ...             {"role": "assistant", "content": "The annual report covers …"},
    ...         ],
    ...     )
    ... )
    >>> print(response.answer)
    >>> for src in response.sources:
    ...     print(src.citation_index, src.source)
    """

    def __init__(
        self,
        retrieval:  RetrievalPipeline,
        llm:        BaseLLMClient,
        condenser:  QueryCondenser,        
    ) -> None:
        self._retrieval  = retrieval
        self._llm        = llm
        self._condenser  = condenser

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def build(cls) -> "RAGPipeline":
        """
        Constructs the full pipeline from settings.
        Builds retrieval, LLM, and condenser sub-components.
        Call once at startup, not per request.
        """
        logger.info("Building RAGPipeline")

        retrieval = RetrievalPipeline.build()

        llm = create_llm_client()

        # Condenser uses low temperature — rewrites must be deterministic
        condenser = QueryCondenser()

        logger.info("RAGPipeline ready")
        return cls(retrieval=retrieval, llm=llm, condenser=condenser)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, request: RAGRequest) -> RAGResponse:
        """
        Runs the full RAG pipeline for a single question.

        Flow:
            question + history
              → QueryCondenser      (rewrite follow-up → standalone query)
              → RetrievalPipeline   (embed → hybrid search → RRF → context)
              → LLMClient.generate  (prompt → LLM → answer)
              → RAGResponse         (answer + attributed sources)

        Args:
            request: RAGRequest with the user's question and optional history.

        Returns:
            RAGResponse containing the grounded answer and source list.
        """
        logger.info(
            "RAG run started",
            question_preview=request.question[:80],
        )

        # 1. Condense: rewrite ambiguous follow-up into a standalone query
        history = getattr(request, "history", []) or []
        retrieval_query = self._condenser.condense(
            question = request.question,
            history  = history,
        )

        logger.info(
            "Using retrieval query",
            retrieval_query_preview=retrieval_query[:80],
        )

        # 2. Retrieve context using the condensed (standalone) query
        retrieval_result = self._retrieval.run(retrieval_query)

        if not retrieval_result.context:
            logger.warning("No context retrieved — returning empty answer")
            return RAGResponse(
                question = request.question,
                answer   = "I was unable to find relevant information in the documents.",
                sources  = [],
            )

        # 3. Generate answer grounded in retrieved context
        #    NOTE: we pass the ORIGINAL question to the LLM, not the rewritten
        #    one — the rewrite was only for retrieval quality improvement.
        answer = self._llm.generate(
            question = request.question,
            context  = retrieval_result.context,
        )
        # 4. Build source list from attributed context
        sources = [
            SourceDoc(
                citation_index = item["citation_index"],
                source         = item['metadata'].get("file_name", ""),
                text           = item.get("text", ""),
            )
            for item in retrieval_result.context
        ]

        logger.info(
            "RAG run complete",
            question_preview=request.question[:80],
            retrieval_query=retrieval_query[:80],
            answer_length=len(answer),
            num_sources=len(sources),
        )

        return RAGResponse(
            question = request.question,
            answer   = answer,
            sources  = sources,
        )

    def stream(self, request: RAGRequest) -> Generator[str, None, None]:
        """
        Streaming variant — yields answer tokens as they arrive.
        Sources are not streamed; call `run()` if you need them.

        Useful for FastAPI StreamingResponse:

            @router.post("/query/stream")
            async def query_stream(request: RAGRequest):
                return StreamingResponse(
                    pipeline.stream(request),
                    media_type="text/plain",
                )

        Args:
            request: RAGRequest with the user's question and optional history.

        Yields:
            Answer string tokens from the Ollama model.
        """
        logger.info(
            "RAG stream started",
            question_preview=request.question[:80],
        )

        # 1. Condense follow-up into a standalone retrieval query
        history = getattr(request, "history", []) or []
        retrieval_query = self._condenser.condense(
            question = request.question,
            history  = history,
        )

        # 2. Retrieve using the condensed query
        retrieval_result = self._retrieval.run(retrieval_query)

        if not retrieval_result.context:
            yield "I was unable to find relevant information in the documents."
            return
        
        # 3. Stream the answer using the ORIGINAL question (not the rewrite)
        yield from self._llm.generate_stream(
            question = request.question,
            context  = retrieval_result.context,
        )