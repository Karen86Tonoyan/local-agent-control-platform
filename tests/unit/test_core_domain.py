from __future__ import annotations

import pytest

from packages.core.domain import (
    ActionIntent,
    AnswerEnvelope,
    CitationItem,
    RequestContext,
    RiskLevel,
    RouteDecision,
)


def test_route_decision_values() -> None:
    assert RouteDecision.ACCEPT == "ACCEPT"
    assert RouteDecision.BLOCK == "BLOCK"
    assert set(RouteDecision) == {"ACCEPT", "VERIFY", "SIMULATE", "ESCALATE", "BLOCK"}


def test_risk_level_values() -> None:
    assert set(RiskLevel) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_action_intent_values() -> None:
    assert ActionIntent.ASK == "ask"
    assert ActionIntent.FIND_BUG == "find-bug"


def test_request_context_defaults() -> None:
    ctx = RequestContext(request_id="abc", prompt="hello")
    assert ctx.source == "api"
    assert ctx.metadata == {}


def test_citation_item_as_dict() -> None:
    c = CitationItem(
        doc_id="d1",
        title="Guide",
        relative_path="docs/guide.md",
        doc_type="documentation",
        chunk_index=2,
        score=0.87,
    )
    d = c.as_dict()
    assert d["doc_id"] == "d1"
    assert d["chunk_index"] == 2
    assert d["score"] == 0.87
    assert set(d.keys()) == {"doc_id", "title", "relative_path", "doc_type", "chunk_index", "score"}


def test_answer_envelope_defaults() -> None:
    env = AnswerEnvelope(request_id="r1", mode="ask", decision="ACCEPT")
    assert env.citations == []
    assert env.warnings == []
    assert env.error is None
    assert env.answer is None


def test_answer_envelope_as_dict_shape() -> None:
    env = AnswerEnvelope(
        request_id="r1",
        mode="route",
        decision="VERIFY",
        warnings=["low confidence"],
        error=None,
    )
    d = env.as_dict()
    assert set(d.keys()) == {"request_id", "mode", "decision", "answer", "citations", "warnings", "error"}
    assert d["warnings"] == ["low confidence"]
    assert d["error"] is None
    assert d["citations"] == []


def test_answer_envelope_with_citations() -> None:
    c = CitationItem("d1", "T", "p/t.md", "doc", 0, 0.9)
    env = AnswerEnvelope(request_id="r2", mode="ask", decision="ACCEPT", citations=[c])
    d = env.as_dict()
    assert len(d["citations"]) == 1
    assert d["citations"][0]["doc_id"] == "d1"


def test_answer_envelope_error_field_always_present() -> None:
    env_ok = AnswerEnvelope(request_id="r3", mode="ask", decision="ACCEPT")
    env_err = AnswerEnvelope(request_id="r4", mode="ask", decision="BLOCK", error="blocked")
    assert env_ok.as_dict()["error"] is None
    assert env_err.as_dict()["error"] == "blocked"
