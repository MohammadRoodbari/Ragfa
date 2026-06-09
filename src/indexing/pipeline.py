from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import get_settings
from src.indexing.embeddings.factory import create_embeddings
from src.indexing.indexer import Indexer
from src.indexing.loaders.base import Document
from src.indexing.loaders.docx_loader import DocxLoader
from src.indexing.loaders.pdf_loader import PdfLoader
from indexing.chunker import HybridSemanticChunker
import structlog

logger = structlog.get_logger()
settings = get_settings()

_LOADER_REGISTRY: dict[str, type[DocxLoader] | type[PdfLoader]] = {
    ".pdf": PdfLoader,
    ".docx": DocxLoader,
}

_MAPPING_PATH = Path(__file__).parents[2] / "config" / "mappings" / "es_index.json"


class IndexingPipeline:
    """
    Top-level indexing pipeline.

    Loader → HybridSemanticChunker → Embedder → Indexer → Elasticsearch
    """

    def __init__(self, indexer: Indexer) -> None:
        self._indexer = indexer

    @classmethod
    def build(cls) -> "IndexingPipeline":
        logger.info("Building IndexingPipeline", index=settings.ES_INDEX)

        chunker = HybridSemanticChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        embedder = create_embeddings()

        es_mapping = _load_mapping(_MAPPING_PATH)

        indexer = Indexer(
            chunker=chunker,
            embedder=embedder,
            index_name=settings.ES_INDEX,
            es_mapping=es_mapping,
        )

        logger.info("IndexingPipeline ready")
        return cls(indexer=indexer)

    def run_file(
        self,
        path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        path = Path(path)
        _assert_supported(path)

        logger.info("Indexing file", path=str(path))

        loader = _LOADER_REGISTRY[path.suffix.lower()]()
        document = loader.load(path)

        merged_metadata = {
            **document.metadata,
            **(metadata or {}),
        }

        enriched_document = Document(
            content=document.content,
            source=document.source,
            metadata=merged_metadata,
            blocks=document.blocks,
        )

        return self._indexer.index_structured_document(
            document=enriched_document,
        )

    def run_directory(
        self,
        directory: Path,
        recursive: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        directory = Path(directory)
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        glob_pattern = "**/*" if recursive else "*"
        files = [
            p for p in directory.glob(glob_pattern)
            if p.is_file() and p.suffix.lower() in _LOADER_REGISTRY
        ]

        if not files:
            logger.warning("No supported files found", directory=str(directory))
            return 0, 0

        logger.info(
            "Indexing directory",
            directory=str(directory),
            num_files=len(files),
        )

        total_success, total_errors = 0, 0

        for file_path in files:
            try:
                success, errors = self.run_file(file_path, metadata=metadata)
                total_success += success
                total_errors += errors
            except Exception as exc:
                logger.error(
                    "Failed to index file — skipping",
                    path=str(file_path),
                    error=str(exc),
                )
                total_errors += 1

        logger.info(
            "Directory indexing complete",
            directory=str(directory),
            total_files=len(files),
            total_success=total_success,
            total_errors=total_errors,
        )
        return total_success, total_errors

    def run_text(
        self,
        text: str,
        source: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> tuple[int, int]:
        logger.info("Indexing raw text")
        return self._indexer.index_document(
            text=text,
            source=source,
            metadata=metadata,
            doc_id=doc_id,
        )


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"ES mapping file not found at {path}. "
            "Make sure config/mappings/es_index.json exists."
        )
    embedder = create_embeddings()
    with path.open() as f:
        mapping = json.load(f)
        mapping["mappings"]["properties"]["embedding"]["dims"] = (
            embedder.embedding_dim
        )
        return mapping


def _assert_supported(path: Path) -> None:
    if path.suffix.lower() not in _LOADER_REGISTRY:
        supported = ", ".join(_LOADER_REGISTRY.keys())
        raise ValueError(
            f"Unsupported file type '{path.suffix}'. Supported: {supported}"
        )
