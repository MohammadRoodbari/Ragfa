"""
API schemas — Pydantic v2 models for all request and response bodies.

These are intentionally separate from ``src/rag/schema.py`` (the internal
pipeline models).  The API layer owns its own contracts and maps to/from the
internal types in the service layer.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Shared ────────────────────────────────────────────────────────────────────

class JobState(str, Enum):
    PENDING  = "PENDING"
    STARTED  = "STARTED"
    SUCCESS  = "SUCCESS"
    FAILURE  = "FAILURE"
    REVOKED  = "REVOKED"


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:        str   = Field(..., examples=["ok"])
    elasticsearch: bool
    redis:         bool

# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestTextRequest(BaseModel):
    """Body for POST /ingest/text"""
    text:   str        = Field(..., min_length=1, description="Raw text to index")
    source: str        = Field(..., min_length=1, description="Human-readable origin label")
    doc_id: str | None = Field(None, description="Stable document ID; auto-generated if omitted")


class IngestJobAccepted(BaseModel):
    """Returned immediately when an ingest job is enqueued (HTTP 202)."""
    task_id:  str
    state:    JobState = JobState.PENDING
    filename: str | None = None
    source:   str | None = None


class IngestJobStatus(BaseModel):
    """Returned by GET /ingest/jobs/{task_id}"""
    task_id:  str
    state:    JobState
    filename: str | None = None
    source:   str | None = None
    progress: int         = Field(0, ge=0, le=100)
    success:  int | None  = None
    errors:   list[str]   = Field(default_factory=list)
    error:    str | None  = None


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Body for POST /query and POST /query/stream"""
    question:   str        = Field(..., min_length=1, description="Natural-language question")
    session_id: str | None = Field(
        None,
        description=(
            "Opaque session identifier for conversation continuity. "
            "If omitted, no history is stored or used."
        ),
    )

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        return v.strip()


class SourceDocument(BaseModel):
    """A single retrieved chunk attributed to the answer."""
    source:    str
    text:      str


class QueryResponse(BaseModel):
    """Full answer with sources (POST /query)."""
    answer:     str
    sources:    list[SourceDocument] = Field(default_factory=list)
    session_id: str | None = None
    model:      str | None = None
    latency_ms: int | None = None


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code:    str
    message: str
    detail:  Any | None = None