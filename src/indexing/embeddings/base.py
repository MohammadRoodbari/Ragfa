from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddings(ABC):
    """
    Common interface for all embedding providers.
    """

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        pass