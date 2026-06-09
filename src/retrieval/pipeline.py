from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.settings import get_settings
from src.indexing.embeddings.base import BaseEmbeddings
from src.indexing.embeddings.factory import create_embeddings
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.searcher import HybridSearcher
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class RetrievalResult:
    """
    The output of a single retrieval run.

    Attributes:
        query:         Original query string.
        context:       Attributed, budget-trimmed context chunks (from ContextBuilder).
        context_block: Ready-to-inject plain-text string for the prompt.
        hits:          Full reranked hit list before budget trimming (for eval / debug).
    """
    query:         str
    context:       list[dict[str, Any]]
    context_block: str
    hits:          list[dict[str, Any]]


class RetrievalPipeline:
    """
    Top-level entry point for the retrieval phase.

    Wires together:
        query → Embedder → HybridSearcher → ContextBuilder

    Typical usage
    -------------
    >>> pipeline = RetrievalPipeline.build()
    >>> result   = pipeline.run("What were the Q3 revenue figures?")
    >>> print(result.context_block)   # inject into your prompt
    """

    def __init__(
        self,
        embedder:        BaseEmbeddings,
        searcher:        HybridSearcher,
        context_builder: ContextBuilder,
    ) -> None:
        self._embedder        = embedder
        self._searcher        = searcher
        self._context_builder = context_builder

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def build(cls) -> "RetrievalPipeline":
        """
        Constructs the pipeline from settings.
        Reuses the same Embedder model as the indexing phase — critical for
        vector-space consistency.
        Call once at startup, not per request.
        """
        logger.info("Building RetrievalPipeline")

        embedder = create_embeddings()

        searcher = HybridSearcher(
            index_name     = settings.ES_INDEX,
            rerank_top_n          = settings.RERANK_TOP_N,
            num_candidates = settings.KNN_NUM_CANDIDATES,
        )
        context_builder = ContextBuilder(
            max_context_tokens = 10000,
        )

        logger.info("RetrievalPipeline ready")
        return cls(
            embedder        = embedder,
            searcher        = searcher,
            context_builder = context_builder,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, query: str) -> RetrievalResult:
        """
        Runs the full retrieval pipeline for a single query.

        Flow:
            query text
              → embed (dense vector)
              → hybrid search (kNN + BM25)
              → RRF rerank
              → context build (dedup + token budget + citations)

        Args:
            query: Natural-language question or search string.

        Returns:
            RetrievalResult with context chunks and a formatted context block.
        """
        logger.info(
            "Starting retrieval",
            query_preview=query[:80],
        )

        # 1. Encode query → dense vector (same model used at index time)
        query_vector = self._embedder.embed_query(query)

        # 2. Hybrid search: kNN + BM25 + RFF rerank
        hits = self._searcher.search(
            query_text   = query,
            query_vector = query_vector,
        )

        if not hits:
            logger.warning(
                "No hits returned from hybrid search",
                query=query,
            )
            return RetrievalResult(
                query         = query,
                context       = [],
                context_block = "",
                hits          = [],
            )

        # 3. Deduplicate, apply token budget, add citation labels
        context = self._context_builder.build(hits)

        # 4. Format as a plain-text block for prompt injection
        context_block = self._context_builder.format_context_block(context)

        logger.info(
            "Retrieval complete",
            query_preview=query[:80],
            num_context=len(context),
        )

        return RetrievalResult(
            query         = query,
            context       = context,
            context_block = context_block,
            hits          = hits,
        )