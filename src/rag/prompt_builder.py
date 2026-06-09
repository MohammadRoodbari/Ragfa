from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


class PromptBuilder:
    """
    Builds reusable LangChain prompt templates and provides helper
    methods for formatting prompt inputs.
    """

    def __init__(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> None:

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("user", user_prompt),
            ]
        )

    @staticmethod
    def format_context(
        context: list[dict],
    ) -> str:
        """
        Format retrieved context into the RAG prompt.
        """

        parts: list[str] = []

        for item in context:

            header = (
                f"[{item['citation_index']}] "
                f"{item.get('source', '')} "
                f"| doc: {item.get('doc_id', '')} "
                f"| chunk: {item.get('chunk_id', '')}"
            )

            parts.append(
                f"{header}\n{item.get('text', '').strip()}"
            )

        return "\n\n---\n\n".join(parts)

    @staticmethod
    def format_history(
        history: list[dict[str, str]],
    ) -> str:
        """
        Format chat history for conversational prompts.
        """

        return "\n".join(
            f"{turn.get('role', 'unknown').capitalize()}: "
            f"{turn.get('content', '').strip()}"
            for turn in history
        )