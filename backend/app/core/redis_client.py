"""
Redis client — async singleton used across the whole application.

Responsibilities
----------------
- Provide a shared AsyncRedis pool (one per process).
- Store / retrieve conversation history so the LLM has memory across turns.
- Key schema:
    chat:{session_id}          → JSON list of {role, content} messages   (TTL: CHAT_TTL_SECONDS)
    job:{task_id}:status       → JSON job-status payload                  (TTL: JOB_TTL_SECONDS)
    job:{task_id}:result       → JSON ingest result                       (TTL: JOB_TTL_SECONDS)
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


# ── Connection management ─────────────────────────────────────────────────────

async def get_redis() -> Redis:
    """Return the module-level singleton, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )
        logger.info("Redis pool created → %s", settings.REDIS_URL)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis pool closed")


async def ping_redis() -> bool:
    try:
        client = await get_redis()
        return await client.ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis ping failed: %s", exc)
        return False


# ── Conversation cache ────────────────────────────────────────────────────────

async def get_conversation(session_id: str) -> list[dict[str, str]]:
    """
    Return the chat history for *session_id* as a list of
    ``{"role": "user"|"assistant", "content": "..."}`` dicts.
    Returns an empty list if no history exists yet.
    """
    client = await get_redis()
    settings = get_settings()
    raw = await client.get(f"chat:{session_id}")
    if raw is None:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Corrupt chat history for session %s — resetting", session_id)
        await client.delete(f"chat:{session_id}")
        return []


async def append_conversation(
    session_id: str,
    role: str,
    content: str,
) -> None:
    """
    Append one turn to the conversation history and reset the TTL.

    Parameters
    ----------
    session_id: str
        Opaque identifier supplied by the caller (e.g. a UUID or user ID).
    role: str
        ``"user"`` or ``"assistant"``.
    content: str
        The message text.
    """
    client = await get_redis()
    settings = get_settings()
    history = await get_conversation(session_id)
    history.append({"role": role, "content": content})

    # Cap history length to avoid unbounded growth
    if len(history) > settings.CHAT_MAX_HISTORY_TURNS * 2:
        history = history[-(settings.CHAT_MAX_HISTORY_TURNS * 2):]

    key = f"chat:{session_id}"
    await client.set(key, json.dumps(history), ex=settings.CHAT_TTL_SECONDS)


async def clear_conversation(session_id: str) -> None:
    """Delete the entire chat history for *session_id*."""
    client = await get_redis()
    await client.delete(f"chat:{session_id}")


# ── Job status cache ──────────────────────────────────────────────────────────

async def set_job_status(task_id: str, payload: dict[str, Any]) -> None:
    client = await get_redis()
    settings = get_settings()
    await client.set(
        f"job:{task_id}:status",
        json.dumps(payload),
        ex=settings.JOB_TTL_SECONDS,
    )


async def get_job_status(task_id: str) -> dict[str, Any] | None:
    client = await get_redis()
    raw = await client.get(f"job:{task_id}:status")
    return json.loads(raw) if raw else None


async def set_job_result(task_id: str, result: dict[str, Any]) -> None:
    client = await get_redis()
    settings = get_settings()
    await client.set(
        f"job:{task_id}:result",
        json.dumps(result),
        ex=settings.JOB_TTL_SECONDS,
    )


async def get_job_result(task_id: str) -> dict[str, Any] | None:
    client = await get_redis()
    raw = await client.get(f"job:{task_id}:result")
    return json.loads(raw) if raw else None