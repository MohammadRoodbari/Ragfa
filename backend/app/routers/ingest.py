"""
Ingest router — /ingest/*

All ingest operations are asynchronous: the HTTP request returns 202 Accepted
immediately with a ``task_id``.  The actual indexing runs in a Celery worker.

Endpoints
---------
POST /ingest/file               — upload PDF or DOCX → enqueue indexing job
POST /ingest/text               — raw text → enqueue indexing job
GET  /ingest/jobs/{task_id}     — poll job status
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, status

from backend.app.dependencies import IngestServiceDep
from backend.app.core.redis_client import get_job_result, get_job_status
from backend.app.schemas.api import IngestJobAccepted, IngestJobStatus, IngestTextRequest, JobState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ── POST /ingest/file ─────────────────────────────────────────────────────────

@router.post(
    "/file",
    response_model=IngestJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and index a PDF or DOCX file",
    description=(
        "Accepts a multipart file upload.  The file is saved and an indexing "
        "job is enqueued via RabbitMQ/Celery.  Poll `/ingest/jobs/{task_id}` "
        "for completion."
    ),
)
async def ingest_file(
    svc: IngestServiceDep,
    file: UploadFile = File(..., description="PDF or DOCX document to index"),
) -> IngestJobAccepted:
    try:
        return await svc.ingest_file(file)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── POST /ingest/text ─────────────────────────────────────────────────────────

@router.post(
    "/text",
    response_model=IngestJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Index raw text directly",
    description=(
        "Index a string of text without uploading a file.  "
        "Useful for programmatic ingestion from other services."
    ),
)
async def ingest_text(
    svc: IngestServiceDep,
    request: IngestTextRequest,
) -> IngestJobAccepted:
    try:
        return await svc.ingest_text(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── GET /ingest/jobs/{task_id} ────────────────────────────────────────────────

@router.get(
    "/jobs/{task_id}",
    response_model=IngestJobStatus,
    summary="Poll ingestion job status",
    description=(
        "Returns the current state of an ingestion job.  "
        "States: PENDING → STARTED → SUCCESS | FAILURE."
    ),
)
async def job_status(task_id: str) -> IngestJobStatus:
    cached = await get_job_status(task_id)
    if cached:
        result = await get_job_result(task_id)
        raw_errors = (result or {}).get("errors", [])
        errors = raw_errors if isinstance(raw_errors, list) else []
        return IngestJobStatus(
            task_id  = task_id,
            state    = JobState(cached.get("state", JobState.PENDING)),
            filename = cached.get("filename"),
            source   = cached.get("source"),
            progress = cached.get("progress", 0),
            success  = (result or {}).get("success"),
            errors   = errors,
            error    = cached.get("error"),
        )

    # Fall back to Celery result backend
    from app.workers.celery_app import celery_app
    async_result = celery_app.AsyncResult(task_id)
    celery_state = async_result.state  # e.g. "PENDING", "SUCCESS", …

    if celery_state == "PENDING":
        # Celery returns PENDING for unknown task IDs — treat as not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )

    meta = async_result.info or {}
    if isinstance(meta, Exception):
        meta = {"error": str(meta)}

    return IngestJobStatus(
        task_id  = task_id,
        state    = JobState(celery_state) if celery_state in JobState._value2member_map_ else JobState.PENDING,
        filename = meta.get("filename"),
        source   = meta.get("source"),
        progress = meta.get("progress", 100 if celery_state == "SUCCESS" else 0),
        success  = meta.get("success"),
        errors   = meta.get("errors", []),
        error    = meta.get("error"),
    )
