from __future__ import annotations

from typing import Any

import structlog
logger = structlog.get_logger(__name__)

# Conservative chars-per-token ratio for a rough token budget estimate.
# GPT-4 / Claude average ~4 chars/token for English prose.
_CHARS_PER_TOKEN = 4


class ContextBuilder:
    """
    Builds the final context window passed to the LLM.

    Responsibilities:
        1. Deduplicate — remove chunks with identical text (can appear when
           the same passage is retrieved via both kNN and BM25 legs).
        2. Token budget — truncate the list so the combined text fits within
           `max_context_tokens`, preserving the highest-ranked chunks.
        3. Source attribution — attach a [1], [2], … citation label to each
           chunk so the prompt builder can inject inline references.

    Output shape (list of dicts):
        {
            "citation_index": 1,          # 1-based label for inline citation
            "chunk_id":       "doc42_chunk_3",
            "doc_id":         "doc42",
            "text":           "...",
            "rrf_score":      0.012345,   # present when coming from reranker
        }
    """

    def __init__(self, max_context_tokens: int = 3000) -> None:
        """
        Args:
            max_context_tokens: Approximate token budget for the context block.
                                Default 3 000 leaves room for system prompt +
                                user query + generation in a 4 096-token window.
        """
        self.max_context_tokens = max_context_tokens
        self._max_chars = max_context_tokens * _CHARS_PER_TOKEN

    # ── Public API ────────────────────────────────────────────────────────────

    def build(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Processes reranked hits into a clean, attributed context list.

        Args:
            hits: Output of RRFReranker.rerank() — sorted by descending RRF score.

        Returns:
            List of context dicts, each with a `citation_index` field, trimmed
            to fit within the token budget.
        """
        if not hits:
            logger.warning("Context builder received empty hit list")
            return []

        logger.info(
            "Building context",
            num_hits=len(hits),
        )

        deduplicated = self._deduplicate(hits)
        budgeted     = self._apply_token_budget(deduplicated)
        attributed   = self._add_citations(budgeted)

        logger.info(
            "Context built",
            original=len(hits),
            after_dedup=len(deduplicated),
            after_budget=len(budgeted),
        )
        return attributed

    def format_context_block(self, context: list[dict[str, Any]]) -> str:
        """
        Renders the context list as a plain-text block for prompt injection.

        Format:
            [1] report_2024.pdf
            chunk text here …

            [2] memo_q3.docx
            another chunk …

        Args:
            context: Output of `build()`.

        Returns:
            A single string ready to be inserted into a prompt template.
        """
        parts = []
        for item in context:
            header = f"[{item['citation_index']}] {item['metadata']['file_name']}"
            parts.append(f"{header}\n{item['text'].strip()}")
        return "\n\n".join(parts)

    # ── Internal steps ────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Removes hits with duplicate text, keeping the first occurrence
        (which has the highest rank after reranking).
        """
        seen_texts: set[str] = set()
        unique = []
        for hit in hits:
            text = hit.get("text", "").strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique.append(hit)
        return unique

    def _apply_token_budget(
        self, hits: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Greedily includes hits until the cumulative character count would
        exceed the token budget. Highest-ranked hits are always included first.
        """
        budgeted   = []
        total_chars = 0

        for hit in hits:
            text_len = len(hit.get("text", ""))
            if total_chars + text_len > self._max_chars:
                logger.info(
                    "Token budget reached",
                    included=len(budgeted),
                    remaining=len(hits) - len(budgeted),
                )
                break
            budgeted.append(hit)
            total_chars += text_len

        return budgeted

    @staticmethod
    def _add_citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Attaches a 1-based citation_index to each hit."""
        return [{**hit, "citation_index": idx} for idx, hit in enumerate(hits, start=1)]