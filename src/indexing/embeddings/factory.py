from config.settings import get_settings

from src.indexing.embeddings.ollama_embeddings import OllamaEmbeddings
from src.indexing.embeddings.openai_embeddings import OpenAIEmbeddings

settings = get_settings()


def create_embeddings():

    if settings.EMBEDDING_PROVIDER == "ollama":
        return OllamaEmbeddings()

    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddings()

    raise ValueError(
        f"Unsupported provider: {settings.EMBEDDING_PROVIDER}"
    )