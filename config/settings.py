from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Elasticsearch ────────────────────────────────────────
    ES_HOST: str
    ES_INDEX: str
    ES_TIMEOUT: int

    # ── Embedding ────────────────────────────────────────────
    EMBEDDING_PROVIDER: Literal["ollama", "openai"]
    EMBEDDING_MODEL: str

    # ── Chunking ─────────────────────────────────────────────
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int

    # ── LLM ──────────────────────────────────────────────────
    LLM_PROVIDER: Literal["ollama", "openai"]
    OLLAMA_BASE_URL: str
    LLM_MODEL: str
    OPENAI_API_KEY: str | None
    OPENAI_BASE_URL: str
    LLM_TEMPERATURE: float

    # ── Retrieval ────────────────────────────────────────────
    RETRIEVAL_TOP_K: int
    RERANK_TOP_N: int
    KNN_NUM_CANDIDATES: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()