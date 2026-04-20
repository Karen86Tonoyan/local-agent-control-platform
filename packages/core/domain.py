from __future__ import annotations

from enum import StrEnum
from typing import Any


class RouteDecision(StrEnum):
    ACCEPT = "ACCEPT"
    VERIFY = "VERIFY"
    SIMULATE = "SIMULATE"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RequestContext:
    """Immutable context attached to a single request lifecycle."""

    __slots__ = ("request_id", "prompt", "source", "metadata")

    def __init__(
        self,
        request_id: str,
        prompt: str,
        source: str = "api",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.request_id = request_id
        self.prompt = prompt
        self.source = source
        self.metadata: dict[str, Any] = metadata or {}


class ActionIntent(StrEnum):
    ASK = "ask"
    EXPLAIN = "explain"
    FIND_BUG = "find-bug"
    NEXT_STEP = "next-step"
    ROUTE = "route"


class CitationItem:
    """Single chunk reference returned in an answer envelope."""

    __slots__ = (
        "doc_id",
        "title",
        "relative_path",
        "doc_type",
        "chunk_index",
        "score",
    )

    def __init__(
        self,
        doc_id: str,
        title: str,
        relative_path: str,
        doc_type: str,
        chunk_index: int,
        score: float,
    ) -> None:
        self.doc_id = doc_id
        self.title = title
        self.relative_path = relative_path
        self.doc_type = doc_type
        self.chunk_index = chunk_index
        self.score = score

    def as_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "relative_path": self.relative_path,
            "doc_type": self.doc_type,
            "chunk_index": self.chunk_index,
            "score": self.score,
        }


class AnswerEnvelope:
    """Canonical response contract for all ALFA-CORE API endpoints."""

    __slots__ = (
        "request_id",
        "mode",
        "decision",
        "answer",
        "citations",
        "warnings",
        "error",
    )

    def __init__(
        self,
        request_id: str,
        mode: str,
        decision: str,
        answer: str | None = None,
        citations: list[CitationItem] | None = None,
        warnings: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        self.request_id = request_id
        self.mode = mode
        self.decision = decision
        self.answer = answer
        self.citations: list[CitationItem] = citations or []
        self.warnings: list[str] = warnings or []
        self.error: str | None = error

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "mode": self.mode,
            "decision": self.decision,
            "answer": self.answer,
            "citations": [c.as_dict() for c in self.citations],
            "warnings": self.warnings,
            "error": self.error,
        }
