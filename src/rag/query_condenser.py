from __future__ import annotations

import structlog

from langchain_core.output_parsers import StrOutputParser

from src.rag.llm.factory import create_llm_client
from src.rag.prompt_builder import PromptBuilder
from src.rag.prompt_repository import PromptRepository

logger = structlog.get_logger(__name__)


class QueryCondenser:
    """
    Rewrites follow-up questions into standalone questions
    before retrieval.
    """

    def __init__(self) -> None:

        self._llm_client = create_llm_client()

        self._prompt_builder = PromptBuilder(
            system_prompt=PromptRepository.load(
                "condense_system.txt"
            ),
            user_prompt=PromptRepository.load(
                "condense_user.txt"
            ),
        )

        self._chain = (
            self._prompt_builder.prompt
            | self._llm_client.llm
            | StrOutputParser()
        )

        logger.info(
            "QueryCondenser initialized",
            provider=type(self._llm_client).__name__,
        )

    def condense(
        self,
        question: str,
        history: list[dict[str, str]],
    ) -> str:
        """
        Rewrite a follow-up question into a standalone question.
        """

        if not history:
            return question

        logger.info(
            "Condensing question",
            question_preview=question[:80],
        )

        standalone = (
            self._chain.invoke(
                {
                    "history": self._prompt_builder.format_history(history),
                    "question": question,
                }
            )
            .strip()
        )

        if not standalone:
            logger.warning(
                "LLM returned an empty question; "
                "falling back to original."
            )
            return question

        logger.info(
            "Question condensed",
            original=question[:80],
            condensed=standalone[:80],
        )

        return standalone