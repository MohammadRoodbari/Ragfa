from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):

    @abstractmethod
    def generate(
        self,
        question: str,
        context: list[dict],
    ) -> str:
        pass

    @abstractmethod
    def generate_stream(
        self,
        question: str,
        context: list[dict],
    ):
        pass