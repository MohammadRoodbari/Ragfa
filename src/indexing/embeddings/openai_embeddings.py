from __future__ import annotations

from typing import Optional

from openai import OpenAI
import structlog

from config.settings import get_settings

from src.indexing.embeddings.base import BaseEmbeddings
from src.indexing.embeddings.ollama_embeddings import EmbeddingError

settings = get_settings()
logger = structlog.get_logger(__name__)


class OpenAIEmbeddings(BaseEmbeddings):

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL,
        api_key: str | None = settings.OPENAI_API_KEY,
        base_url: str = settings.OPENAI_BASE_URL,
    ) -> None:

        self.model_name = model_name

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        self._embedding_dim: Optional[int] = None

        logger.info(
            "OpenAIEmbeddings initialised",
            model=model_name,
            base_url=base_url,
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        embeddings = self._call_embed(texts)

        self._cache_dim(embeddings[0])

        return embeddings

    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        if not text:
            raise ValueError("Query text must be non-empty.")

        embedding = self._call_embed([text])[0]

        self._cache_dim(embedding)

        return embedding

    @property
    def embedding_dim(self) -> int:

        if self._embedding_dim is None:
            self.embed_query("probe")

        return self._embedding_dim

    def _call_embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        try:
            response = self._client.embeddings.create(
                model=self.model_name,
                input=texts,
            )

        except Exception as exc:
            raise EmbeddingError(
                self.model_name,
                str(exc),
                exc,
            ) from exc

        embeddings = [
            item.embedding
            for item in response.data
        ]

        if not embeddings:
            raise EmbeddingError(
                self.model_name,
                "Empty embeddings returned.",
            )

        return embeddings

    def _cache_dim(
        self,
        embedding: list[float],
    ) -> None:

        if self._embedding_dim is None:
            self._embedding_dim = len(embedding)