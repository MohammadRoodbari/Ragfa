from __future__ import annotations

from typing import List, Optional

import ollama
from ollama import ResponseError
from src.indexing.embeddings.base import BaseEmbeddings
from config.settings import get_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()


class EmbeddingError(RuntimeError):
    """Raised when the Ollama embedding call fails."""

    def __init__(self, model: str, reason: str, original: Exception | None = None) -> None:
        super().__init__(f"Embedding failed for model '{model}': {reason}")
        self.model = model
        self.reason = reason
        self.__cause__ = original


class OllamaEmbeddings(BaseEmbeddings):
    """
    Thin, stateful wrapper around an Ollama embedding model.

    Responsibilities
    ----------------
    - Encode a batch of texts (``embed_documents``) or a single query
      string (``embed_query``) into dense float vectors.
    - Cache the embedding dimension after the first successful call so
      downstream components (e.g. ES index creation) can query it without
      an extra network round-trip.

    Parameters
    ----------
    model_name:
        Ollama model tag, e.g. ``"nomic-embed-text"``.
    base_url:
        Base URL of the running Ollama server.
    """

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL,
        base_url: str = settings.OLLAMA_BASE_URL,
    ) -> None:
        self.model_name = model_name
        self._client = ollama.Client(host=base_url)
        self._embedding_dim: Optional[int] = None

        logger.info(
            "OllamaEmbeddings initialised",
            model=model_name,
            base_url=base_url,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts in a single batched request.

        Parameters
        ----------
        texts:
            Non-empty list of strings to encode.

        Returns
        -------
        List of float vectors, one per input text.

        Raises
        ------
        EmbeddingError
            If the Ollama call fails or returns an unexpected response.
        """
        if not texts:
            logger.debug("embed_documents called with empty list — returning []")
            return []

        logger.debug(
            "Embedding document batch",
            model=self.model_name,
            num_texts=len(texts),
        )

        embeddings = self._call_embed(texts)
        self._cache_dim(embeddings[0])

        logger.debug(
            "Document batch embedded",
            model=self.model_name,
            num_embeddings=len(embeddings),
            dim=self._embedding_dim,
        )
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query string.

        Parameters
        ----------
        text:
            The query to encode.

        Returns
        -------
        A single float vector.

        Raises
        ------
        EmbeddingError
            If the Ollama call fails or returns an unexpected response.
        """
        if not text:
            raise ValueError("Query text must be a non-empty string.")

        logger.debug(
            "Embedding query",
            model=self.model_name,
        )

        embeddings = self._call_embed(text)
        embedding = embeddings[0]
        self._cache_dim(embedding)

        logger.debug(
            "Query embedded",
            model=self.model_name,
            dim=self._embedding_dim,
        )
        return embedding

    @property
    def embedding_dim(self) -> int:
        """
        Embedding vector dimensionality.

        Performs a lightweight probe call on first access if the dimension
        has not yet been cached from a prior embed call.
        """
        if self._embedding_dim is None:
            logger.debug(
                "Dimension not yet cached — sending probe request",
                model=self.model_name,
            )
            self.embed_query("probe")
        return self._embedding_dim  # type: ignore[return-value]

    def _call_embed(self, input: str | List[str]) -> List[List[float]]:
        """
        Execute the Ollama embed call and normalise the response.

        Raises
        ------
        EmbeddingError
            Wraps any ``ResponseError`` or unexpected response shape.
        """
        try:
            response = self._client.embed(model=self.model_name, input=input)
        except ResponseError as exc:
            logger.error(
                "Ollama ResponseError during embed",
                model=self.model_name,
                error=str(exc),
            )
            raise EmbeddingError(
                model=self.model_name,
                reason=str(exc),
                original=exc,
            ) from exc

        embeddings: List[List[float]] = response.embeddings

        if not embeddings:
            raise EmbeddingError(
                model=self.model_name,
                reason="API returned an empty embeddings list",
            )

        return embeddings

    def _cache_dim(self, embedding: List[float]) -> None:
        """Store the vector dimension on first observation."""
        if self._embedding_dim is None:
            self._embedding_dim = len(embedding)
            logger.debug(
                "Embedding dimension cached",
                model=self.model_name,
                dim=self._embedding_dim,
            )