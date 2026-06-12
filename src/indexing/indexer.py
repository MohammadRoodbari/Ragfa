from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from src.core.es_client import bulk_index, create_index_if_not_exists
from src.indexing.embeddings.base import BaseEmbeddings
from src.indexing.loaders.base import Document
from src.indexing.chunker import HybridSemanticChunker

logger = logging.getLogger(__name__)


class Indexer:
    """
    Orchestrates document indexing:
        Document/text → chunks → embeddings → Elasticsearch
    """

    def __init__(
        self,
        chunker: HybridSemanticChunker,
        embedder: BaseEmbeddings,
        index_name: str,
        es_mapping: dict[str, Any],
    ) -> None:
        self.chunker = chunker
        self.embedder = embedder
        self.index_name = index_name

        create_index_if_not_exists(index=self.index_name, mapping=es_mapping)

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def index_document(
        self,
        text: str,
        source: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> tuple[int, int]:
        """
        Backward-compatible indexing for raw text.
        """
        document = Document(
            content=text,
            source=source,
            metadata=metadata or {},
            blocks=[],
        )
        return self.index_structured_document(document=document, doc_id=doc_id)

    def index_structured_document(
        self,
        document: Document,
        doc_id: str | None = None,
    ) -> tuple[int, int]:
        """
        Preferred indexing path for structured documents.
        """
        doc_id = doc_id or _make_doc_id(document.source)

        logger.info(
            "Starting document indexing",
            extra={
                "source": document.source,
                "doc_id": doc_id,
            },
        )


        chunks = self.chunker.chunk_document(document)
        if not chunks:
            logger.warning(
                "No chunks produced — document may be empty",
                extra={"source": document.source},
            )
            return 0, 0

        logger.info(
            "Document chunked",
            extra={
                "doc_id": doc_id,
                "num_chunks": len(chunks),
            },
        )

        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_documents(chunk_texts)

        es_docs = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_chunk_{idx}"
            es_doc = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "text": chunk.text,
                "embedding": embedding,
                "metadata": document.metadata,
                "chunk_index": chunk.chunk_index,
            }

            es_docs.append(es_doc)

        success, errors = bulk_index(es_docs, index=self.index_name)

        logger.info(
            "Document indexing complete",
            extra={
                "doc_id": doc_id,
                "source": document.source,
                "success": success,
                "errors": errors,
            },
        )
        return success, errors

    def index_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> tuple[int, int]:
        total_success, total_errors = 0, 0

        for doc in documents:
            success, errors = self.index_document(
                text=doc["text"],
                source=doc["source"],
                metadata=doc.get("metadata"),
                doc_id=doc.get("doc_id"),
            )
            total_success += success
            total_errors += errors

        logger.info(
            "Batch indexing complete",
            extra={
                "total_documents": len(documents),
                "total_success": total_success,
                "total_errors": total_errors,
            },
        )
        return total_success, total_errors


def _make_doc_id(source: str) -> str:
    if not source:
        return str(uuid.uuid4())
    return hashlib.md5(source.encode()).hexdigest()[:16]
