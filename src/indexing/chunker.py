from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import get_settings
from src.indexing.loaders.base import Document, DocumentBlock

logger = logging.getLogger(__name__)
settings = get_settings()

_DEFAULT_SEPARATORS: List[str] = ["\n\n", "\n", ".", " ", ""]


@dataclass
class Chunk:
    """
    Structured chunk emitted by the chunking layer.

    Attributes
    ----------
    text:
        Final chunk text to embed/index.
    chunk_index:
        Sequential chunk number within the document.
    section_path:
        Hierarchical heading path, e.g.
        ["Introduction", "Methods", "Data Collection"]
    block_types:
        Semantic block types included in this chunk.
    metadata:
        Arbitrary chunk-level metadata.
    """

    text: str
    chunk_index: int
    section_path: list[str] = field(default_factory=list)
    block_types: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class HybridSemanticChunker:
    """
    Hybrid semantic chunker for structured documents.

    Strategy
    --------
    1. Use document semantic blocks if available.
    2. Build section-aware groups using headings.
    3. Merge adjacent blocks up to chunk_size.
    4. If a block/section exceeds chunk_size, recursively split it.
    5. Fallback to text-only recursive splitting when blocks are unavailable.

    This balances:
    - document structure preservation
    - semantic coherence
    - embedding-friendly chunk size control
    """

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        separators: List[str] = _DEFAULT_SEPARATORS,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be smaller than "
                f"chunk_size ({chunk_size})."
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
        )

        logger.debug(
            "HybridSemanticChunker initialised",
            extra={
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
        )

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def chunk_document(self, document: Document) -> list[Chunk]:
        """
        Chunk a structured Document.

        Uses semantic blocks when present; falls back to text chunking otherwise.
        """
        if document.blocks:
            chunks = self._chunk_blocks(document.blocks)
        else:
            chunks = self._chunk_text_fallback(document.content)

        logger.debug(
            "Document chunked semantically",
            extra={
                "source": document.source,
                "num_blocks": len(document.blocks),
                "num_chunks": len(chunks),
            },
        )
        return chunks

    def chunk_text(self, text: str) -> list[Chunk]:
        """
        Chunk raw text without structure.
        """
        return self._chunk_text_fallback(text)

    # ------------------------------------------------------------------ #
    # Block-aware chunking                                               #
    # ------------------------------------------------------------------ #

    def _chunk_blocks(self, blocks: list[DocumentBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []

        current_heading_path: list[str] = []
        current_buffer: list[DocumentBlock] = []
        current_block_types: list[str] = []

        def flush_buffer() -> None:
            nonlocal current_buffer, current_block_types, chunks

            if not current_buffer:
                return

            combined_text = "\n".join(block.text for block in current_buffer).strip()
            if not combined_text:
                current_buffer = []
                current_block_types = []
                return

            if len(combined_text) <= self.chunk_size:
                chunks.append(
                    Chunk(
                        text=combined_text,
                        chunk_index=len(chunks),
                        section_path=current_heading_path.copy(),
                        block_types=list(dict.fromkeys(current_block_types)),
                    )
                )
            else:
                subchunks = self._splitter.split_text(combined_text)
                for subchunk in subchunks:
                    subchunk = subchunk.strip()
                    if not subchunk:
                        continue
                    chunks.append(
                        Chunk(
                            text=subchunk,
                            chunk_index=len(chunks),
                            section_path=current_heading_path.copy(),
                            block_types=list(dict.fromkeys(current_block_types)),
                        )
                    )

            current_buffer = []
            current_block_types = []

        for block in blocks:
            if block.type == "heading":
                flush_buffer()
                self._update_heading_path(current_heading_path, block)
                continue

            block_text = block.text.strip()
            if not block_text:
                continue

            candidate_parts = [b.text for b in current_buffer] + [block_text]
            candidate_text = "\n".join(candidate_parts)

            if current_buffer and len(candidate_text) > self.chunk_size:
                flush_buffer()

            if len(block_text) > self.chunk_size:
                split_blocks = self._splitter.split_text(block_text)
                for piece in split_blocks:
                    piece = piece.strip()
                    if not piece:
                        continue
                    chunks.append(
                        Chunk(
                            text=piece,
                            chunk_index=len(chunks),
                            section_path=current_heading_path.copy(),
                            block_types=[block.type],
                        )
                    )
                continue

            current_buffer.append(block)
            current_block_types.append(block.type)

        flush_buffer()

        return self._apply_overlap(chunks)

    def _update_heading_path(
        self,
        heading_path: list[str],
        block: DocumentBlock,
    ) -> None:
        """
        Maintain hierarchical heading path based on heading level.
        """
        level = block.level or 1

        while len(heading_path) >= level:
            heading_path.pop()

        heading_path.append(block.text)

    # ------------------------------------------------------------------ #
    # Fallback text chunking                                             #
    # ------------------------------------------------------------------ #

    def _chunk_text_fallback(self, text: str) -> list[Chunk]:
        if not text or not text.strip():
            logger.warning("chunk_text received empty or whitespace-only text")
            return []

        parts = self._splitter.split_text(text)
        return [
            Chunk(
                text=part.strip(),
                chunk_index=i,
                section_path=[],
                block_types=[],
            )
            for i, part in enumerate(parts)
            if part.strip()
        ]

    # ------------------------------------------------------------------ #
    # Optional overlap enrichment                                        #
    # ------------------------------------------------------------------ #

    def _apply_overlap(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Applies lightweight prefix overlap between neighboring chunks.

        Since semantic chunking already preserves coherence, we keep this simple:
        prepend tail text from previous chunk when beneficial.
        """
        if not chunks or self.chunk_overlap <= 0:
            return chunks

        enriched: list[Chunk] = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                enriched.append(chunk)
                continue

            prev_text = enriched[-1].text
            overlap_text = prev_text[-self.chunk_overlap :].strip()

            merged_text = chunk.text
            if overlap_text and not chunk.text.startswith(overlap_text):
                merged_text = f"{overlap_text}\n{chunk.text}"

            enriched.append(
                Chunk(
                    text=merged_text,
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.metadata,
                )
            )

        return enriched
