from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from src.rag.llm.base import BaseLLMClient
from config.settings import get_settings
from src.rag.prompt_builder import PromptBuilder
import structlog


settings = get_settings()
logger = structlog.get_logger(__name__)

class OllamaClient(BaseLLMClient):
    """
    Ollama LLM client wired to the RAG prompt.

    Wraps LangChain's ChatOllama and composes it with the PromptBuilder
    into a single invokable chain:

        prompt | ChatOllama | StrOutputParser

    Keeping the LLM client separate from the pipeline means you can
    swap Ollama for OpenAI or vLLM by replacing only this class.
    """

    def __init__(
        self,
        model:    str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """
        Args:
            model:          Ollama model tag (e.g. "llama3", "mistral").
                            Defaults to settings.llm_model_name.
            base_url:       Ollama server URL. Defaults to settings.llm_base_url.
            temperature:    Sampling temperature. Defaults to settings.llm_temperature.
            prompt_builder: PromptBuilder instance. A default one is created if omitted.
        """
        self._prompt_builder = prompt_builder or PromptBuilder()

        self._llm = ChatOllama(
            model       = model       or settings.OLLAMA_MODEL,
            base_url    = base_url    or settings.OLLAMA_BASE_URL,
            temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE,
        )

        self._chain = self._prompt_builder.prompt | self._llm | StrOutputParser()

        logger.info(
            "LLMClient initialised",
            model=model or settings.OLLAMA_MODEL,
            base_url=base_url or settings.OLLAMA_BASE_URL,
        )
    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, question: str, context: list[dict]) -> str:
        """
        Generates an answer grounded in the provided context chunks.

        Args:
            question: The user's natural-language question.
            context:  Attributed context list from ContextBuilder.build().
                      Each dict must have at minimum: citation_index, source,
                      doc_id, chunk_id, text.

        Returns:
            The model's answer as a plain string.
        """
        logger.info(
            "Generating answer",
            question_preview=question[:80],
        )

        formatted_context = self._prompt_builder.format_context(context)

        answer = self._chain.invoke({
            "question": question,
            "context":  formatted_context,
        })

        logger.info(
            "Answer generated",
            answer_length=len(answer),
        )
        return answer

    def generate_stream(self, question: str, context: list[dict]):
        """
        Streaming variant — yields answer tokens as they arrive.
        Useful for FastAPI StreamingResponse.

        Args:
            question: The user's natural-language question.
            context:  Same as `generate()`.

        Yields:
            Answer string tokens (str) from the model.
        """
        logger.info(
            "Streaming answer",
            question_preview=question[:80],
        )

        formatted_context = self._prompt_builder.format_context(context)

        for chunk in self._chain.stream({
            "question": question,
            "context":  formatted_context,
        }):
            yield chunk
