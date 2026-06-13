"""
Celery tasks for document ingestion.

Both tasks follow the same lifecycle:
  PENDING → STARTED → SUCCESS | FAILURE

Status is mirrored to Redis (job:{task_id}:status) so the HTTP layer
can poll without hitting the Celery result backend directly.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from backend.app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _update_status(task: Task, state: str, meta: dict[str, Any]) -> None:
    """Push status to Celery backend and mirror it to Redis synchronously."""
    task.update_state(state=state, meta=meta)

    # Run the async Redis helper in a one-shot event loop so Celery
    # (synchronous) tasks can still update the cache.
    async def _push() -> None:
        from backend.app.core.redis_client import set_job_status
        await set_job_status(task.request.id, {"state": state, **meta})

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_push())
        else:
            loop.run_until_complete(_push())
    except Exception:  # noqa: BLE001
        pass  # status mirror is best-effort; don't fail the task


# ── Tasks ─────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="backend.app.workers.ingest_tasks.ingest_file",
    max_retries=3,
    default_retry_delay=10,
)
def ingest_file_task(
    self: Task,
    file_path: str,
    original_filename: str,
) -> dict[str, Any]:
    """
    Index a document from *file_path*.

    Parameters
    ----------
    file_path:
        Absolute path to the (already saved) temporary file.
    original_filename:
        Original upload filename — used for source attribution in ES.

    Returns
    -------
    dict with keys ``success`` (int) and ``errors`` (list[str]).
    """
    _update_status(self, "STARTED", {"filename": original_filename, "progress": 0})
    logger.info("ingest_file | task=%s file=%s", self.request.id, original_filename)

    try:
        # Import here to keep Celery worker startup fast and avoid
        # loading heavyweight models until the task actually runs.
        from src.indexing.pipeline import IndexingPipeline

        pipeline = IndexingPipeline.build()

        _update_status(self, "STARTED", {"filename": original_filename, "progress": 20})
        success, errors = pipeline.run_file(Path(file_path))

        result = {
            "filename": original_filename,
            "success": success,
            "errors": errors,
        }

        async def _save_result() -> None:
            from backend.app.core.redis_client import set_job_result
            await set_job_result(self.request.id, result)

        asyncio.get_event_loop().run_until_complete(_save_result())

        _update_status(self, "SUCCESS", result)
        return result

    except SoftTimeLimitExceeded:
        msg = f"Task timed out while indexing {original_filename}"
        logger.error(msg)
        _update_status(self, "FAILURE", {"error": msg})
        raise

    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest_file failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _update_status(self, "FAILURE", {"error": str(exc)})
            raise

    finally:
        # Always clean up the temp file regardless of outcome
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass


@celery_app.task(
    bind=True,
    name="backend.app.workers.ingest_tasks.ingest_text",
    max_retries=3,
    default_retry_delay=10,
)
def ingest_text_task(
    self: Task,
    text: str,
    source: str,
    doc_id: str | None,
) -> dict[str, Any]:
    """
    Index raw text passed directly as a string.

    Parameters
    ----------
    text:    The raw content to chunk and embed.
    source:  A human-readable label (e.g. filename, URL, "manual").
    doc_id:  Optional stable identifier; auto-generated if omitted.
    """
    _update_status(self, "STARTED", {"source": source, "progress": 0})
    logger.info("ingest_text | task=%s source=%s", self.request.id, source)

    try:
        from src.indexing.pipeline import IndexingPipeline

        pipeline = IndexingPipeline.build()
        success, errors = pipeline.run_text(text=text, source=source, doc_id=doc_id)

        result = {"source": source, "success": success, "errors": errors}

        async def _save() -> None:
            from backend.app.core.redis_client import set_job_result
            await set_job_result(self.request.id, result)

        asyncio.get_event_loop().run_until_complete(_save())

        _update_status(self, "SUCCESS", result)
        return result

    except SoftTimeLimitExceeded:
        msg = f"Task timed out while indexing source='{source}'"
        _update_status(self, "FAILURE", {"error": msg})
        raise

    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest_text failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _update_status(self, "FAILURE", {"error": str(exc)})
            raise