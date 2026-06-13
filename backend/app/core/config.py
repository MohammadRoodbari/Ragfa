from __future__ import annotations
from functools import lru_cache
from typing import Literal
from config.settings import Settings as _BaseSettings


class BackendSettings(_BaseSettings):
    """Extends the RAG core settings with backend-specific vars."""

    
    # ── Application ──────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"]
    LOG_LEVEL: str

    # ── Elasticsearch auth (backend only) ────────────────────
    ES_USERNAME: str | None
    ES_PASSWORD: str | None

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int
    CHAT_TTL_SECONDS: int
    CHAT_MAX_HISTORY_TURNS: int
    JOB_TTL_SECONDS: int

    # ── Celery / RabbitMQ ────────────────────────────────────
    RABBITMQ_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_TIMEOUT: int

    # ── File upload ──────────────────────────────────────────
    UPLOAD_MAX_BYTES: int
    UPLOAD_TMP_DIR: str

@lru_cache(maxsize=1)
def get_settings() -> BackendSettings:
    return BackendSettings()