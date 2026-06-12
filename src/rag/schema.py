from __future__ import annotations

from pydantic import BaseModel, Field


class SourceDoc(BaseModel):
    """A single attributed source chunk returned with the answer."""
    citation_index: int    = Field(..., description="1-based citation label used in the answer")
    source:         str    = Field(..., description="Source filename or URL")
    text:           str    = Field(..., description="Chunk text used as context")


class RAGRequest(BaseModel):
    """Input to the RAG pipeline."""
    question: str = Field(..., min_length=1, description="User's natural-language question")
    history: list[dict[str, str]] = []

class RAGResponse(BaseModel):
    """Output of the RAG pipeline."""
    question: str             = Field(..., description="Original question")
    answer:   str             = Field(..., description="LLM-generated answer grounded in context")
    sources:  list[SourceDoc] = Field(default_factory=list, description="Context chunks used")
