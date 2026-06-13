from config.settings import get_settings

from src.rag.llm.ollama_client import OllamaClient
from src.rag.llm.openai_client import OpenAIClient

settings = get_settings()


def create_llm_client():

    if settings.LLM_PROVIDER == "ollama":
        return OllamaClient()

    if settings.LLM_PROVIDER == "openai":
        return OpenAIClient()

    raise ValueError(
        f"Unsupported LLM provider: {settings.LLM_PROVIDER}"
    )