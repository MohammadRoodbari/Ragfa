from __future__ import annotations

import structlog

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from config.settings import get_settings
from src.rag.prompt_builder import PromptBuilder

from src.rag.llm.base import BaseLLMClient

settings = get_settings()
logger = structlog.get_logger(__name__)


class OpenAIClient(BaseLLMClient):

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        prompt_builder: PromptBuilder | None = None,
    ):

        self._prompt_builder = prompt_builder or PromptBuilder()

        self._llm = ChatOpenAI(
            model=model or settings.OPENAI_MODEL,
            api_key=api_key or settings.OPENAI_API_KEY,
            base_url=base_url or settings.OPENAI_BASE_URL,
            temperature=temperature
            if temperature is not None
            else settings.LLM_TEMPERATURE,
        )

        self._chain = (
            self._prompt_builder.prompt
            | self._llm
            | StrOutputParser()
        )

        logger.info(
            "OpenAI client initialized",
            model=model or settings.OPENAI_MODEL,
        )

    def generate(
        self,
        question: str,
        context: list[dict],
    ) -> str:

        formatted_context = self._prompt_builder.format_context(context)

        return self._chain.invoke(
            {
                "question": question,
                "context": formatted_context,
            }
        )

    def generate_stream(
        self,
        question: str,
        context: list[dict],
    ):

        formatted_context = self._prompt_builder.format_context(context)

        yield from self._chain.stream(
            {
                "question": question,
                "context": formatted_context,
            }
        )