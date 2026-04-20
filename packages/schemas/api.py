from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RouteRequestSchema(BaseModel):
    prompt: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AskRequestSchema(BaseModel):
    prompt: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationSchema(BaseModel):
    doc_id: str
    title: str
    relative_path: str
    doc_type: str
    chunk_index: int
    score: float


class AnswerEnvelopeSchema(BaseModel):
    """Canonical response contract for all ALFA-CORE API endpoints."""

    request_id: str
    mode: str
    decision: str
    answer: str | None = None
    citations: list[CitationSchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
