"""
IngestService — thin orchestration layer between the HTTP routers and
the Celery workers.

Responsibilities
----------------
- Validate and persist the uploaded file to a deterministic temp path.
- Enqueue the appropriate Celery task.
- Mirror PENDING status to Redis immediately (so a poll right after
  202 Accepted never returns 404).
- Return a typed ``IngestJobAccepted`` response.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from backend.app.core.config import get_settings
from backend.app.core.redis_client import set_job_status
from backend.app.schemas.api import IngestJobAccepted, IngestTextRequest, JobState
from backend.app.workers.ingest_tasks import ingest_file_task, ingest_text_task

logger = logging.getLogger(__name__)

_ALLOWED_SUFFIXES = {".pdf", ".docx"}


class IngestService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._tmp_dir = Path(self._settings.UPLOAD_TMP_DIR)
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    # ── File ingestion ────────────────────────────────────────────────────────

    async def ingest_file(self, upload: UploadFile) -> IngestJobAccepted:
        """
        Validate *upload*, persist it to disk, enqueue ``ingest_file_task``.

        Parameters
        ----------
        upload: fastapi.UploadFile
            The multipart file from the HTTP request.

        Returns
        -------
        IngestJobAccepted
            Contains the Celery task ID the caller can poll.

        Raises
        ------
        ValueError
            If the file type is unsupported or the file exceeds the size limit.
        """
        filename = upload.filename or "upload"
        suffix = Path(filename).suffix.lower()

        if suffix not in _ALLOWED_SUFFIXES:
            raise ValueError(
                f"Unsupported file type '{suffix}'. "
                f"Allowed: {', '.join(sorted(_ALLOWED_SUFFIXES))}"
            )

        # Read content with size guard
        content = await upload.read()
        if len(content) > self._settings.UPLOAD_MAX_BYTES:
            raise ValueError(
                f"File exceeds the {self._settings.UPLOAD_MAX_BYTES // (1024 * 1024)} MB limit."
            )

        # Save to a unique path so concurrent uploads never collide
        unique_name = f"{uuid.uuid4().hex}{suffix}"
        tmp_path = self._tmp_dir / unique_name
        tmp_path.write_bytes(content)

        logger.info("Saved upload → %s (%d bytes)", tmp_path, len(content))

        # Enqueue task (Celery takes it from here)
        task = ingest_file_task.apply_async(
            args=[str(tmp_path), filename],
            queue="ingest",
        )

        await set_job_status(
            task.id,
            {"state": JobState.PENDING, "filename": filename, "progress": 0},
        )

        logger.info("Enqueued ingest_file | task=%s filename=%s", task.id, filename)
        return IngestJobAccepted(task_id=task.id, filename=filename)

    # ── Text ingestion ────────────────────────────────────────────────────────

    async def ingest_text(self, request: IngestTextRequest) -> IngestJobAccepted:
        """
        Enqueue ``ingest_text_task`` for raw text.

        Parameters
        ----------
        request: IngestTextRequest
            Validated API schema with text, source, and optional doc_id.
        """
        task = ingest_text_task.apply_async(
            args=[request.text, request.source, request.doc_id],
            queue="ingest",
        )

        await set_job_status(
            task.id,
            {"state": JobState.PENDING, "source": request.source, "progress": 0},
        )

        logger.info("Enqueued ingest_text | task=%s source=%s", task.id, request.source)
        return IngestJobAccepted(task_id=task.id, source=request.source)