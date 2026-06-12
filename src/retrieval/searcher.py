from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog
from elasticsearch import RequestError

from config.settings import get_settings
from src.core.es_client import get_es_client

logger = structlog.get_logger(__name__)
settings = get_settings()

_SOURCE_FIELDS = ["chunk_id", "doc_id", "metadata", "text"]


class HybridSearcher:
    """
    Hybrid retrieval without Elastic's paid RRF retriever.

    Strategy:
      1) Run a lexical search (BM25) query.
      2) Run a semantic kNN query.
      3) Fuse both ranked lists locally with Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        index_name: str | None = None,
        rerank_top_n: int | None = None,
        num_candidates: int | None = None,
        lexical_top_k: int | None = None,
        semantic_top_k: int | None = None,
        rrf_k: int = 60,
    ) -> None:
        self.index_name = index_name or settings.ES_INDEX
        self.rerank_top_n = rerank_top_n or settings.RERANK_TOP_N
        self.top_k = settings.RETRIEVAL_TOP_K
        self.num_candidates = num_candidates or settings.KNN_NUM_CANDIDATES

        # Fetch a larger candidate pool than the final context window.
        self.lexical_top_k = lexical_top_k or max(self.top_k * 4, 50)
        self.semantic_top_k = semantic_top_k or max(self.top_k * 4, 50)

        self.rrf_k = rrf_k

    def search(
        self,
        query_text: str,
        query_vector: list[float],
    ) -> list[dict[str, Any]]:
        logger.info(
            "Running hybrid search (local RRF)",
            index=self.index_name,
            top_k=self.top_k,
            lexical_top_k=self.lexical_top_k,
            semantic_top_k=self.semantic_top_k,
            query_preview=query_text[:80],
        )

        client = get_es_client()

        try:
            lexical_hits = self._search_lexical(client, query_text)
            semantic_hits = self._search_semantic(client, query_vector)
        except RequestError as exc:
            logger.error("Hybrid search failed", error=str(exc))
            raise

        fused = self._rrf_fuse([lexical_hits, semantic_hits])

        logger.info(
            "Hybrid search complete",
            lexical_hits=len(lexical_hits),
            semantic_hits=len(semantic_hits),
            returned=len(fused),
        )
        return fused

    def _search_lexical(
        self,
        client: Any,
        query_text: str,
    ) -> list[dict[str, Any]]:
        body = {
            "size": self.lexical_top_k,
            "query": {
                "match": {
                    "text": {
                        "query": query_text,
                    }
                }
            },
        }

        response = client.search(
            index=self.index_name,
            body=body,
            source=_SOURCE_FIELDS,
        )
        return self._parse_hits(response)

    def _search_semantic(
        self,
        client: Any,
        query_vector: Sequence[float],
    ) -> list[dict[str, Any]]:
        body = {
            "size": self.semantic_top_k,
            "knn": {
                "field": "embedding",
                "query_vector": list(query_vector),
                "k": self.semantic_top_k,
                "num_candidates": max(self.num_candidates, self.semantic_top_k),
            },
        }

        response = client.search(
            index=self.index_name,
            body=body,
            source=_SOURCE_FIELDS,
        )
        return self._parse_hits(response)

    def _rrf_fuse(
        self,
        rank_lists: list[list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Reciprocal Rank Fusion:
            RRF(d) = sum(1 / (k + rank_i(d)))

        We keep the best source hit payload for each document and attach rrf_score.
        """
        scores: dict[str, float] = {}
        best_hit: dict[str, dict[str, Any]] = {}

        for rank_list in rank_lists:
            for rank, hit in enumerate(rank_list, start=1):
                doc_id = hit["_id"]
                scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (self.rrf_k + rank))

                if doc_id not in best_hit:
                    best_hit[doc_id] = hit

        ordered_ids = sorted(scores, key=scores.get, reverse=True)

        fused: list[dict[str, Any]] = []
        for doc_id in ordered_ids[: self.rerank_top_n]:
            hit = {
                **best_hit[doc_id],
                "rrf_score": round(scores[doc_id], 8),
            }
            fused.append(hit)

        return fused

    @staticmethod
    def _parse_hits(response: dict[str, Any]) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        for h in response["hits"]["hits"]:
            source = h.get("_source") or {}
            hits.append(
                {
                    "_id": h["_id"],
                    "_score": h.get("_score"),
                    **source,
                }
            )
        return hits