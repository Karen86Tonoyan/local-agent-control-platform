from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.telemetry.audit import AuditLogger


@pytest.fixture()
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "logs" / "audit.jsonl"


@pytest.fixture()
def logger(audit_path: Path) -> AuditLogger:
    return AuditLogger(path=audit_path)


def _read_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_log_creates_file(logger: AuditLogger, audit_path: Path) -> None:
    logger.log(
        prompt="hello",
        route_decision="ACCEPT",
        final_decision="ACCEPT",
        reason="ok",
        source="test",
        duration_ms=1,
    )
    assert audit_path.exists()


def test_log_record_fields(logger: AuditLogger, audit_path: Path) -> None:
    logger.log(
        prompt="test prompt",
        route_decision="VERIFY",
        final_decision="ESCALATE",
        reason="high impact",
        source="test.unit",
        duration_ms=42,
    )
    records = _read_records(audit_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["route_decision"] == "VERIFY"
    assert rec["final_decision"] == "ESCALATE"
    assert rec["reason"] == "high impact"
    assert rec["source"] == "test.unit"
    assert rec["duration_ms"] == 42
    assert "timestamp" in rec
    assert "prompt_hash" in rec


def test_log_no_raw_prompt_in_record(logger: AuditLogger, audit_path: Path) -> None:
    secret = "super secret prompt content"
    logger.log(
        prompt=secret,
        route_decision="ACCEPT",
        final_decision="ACCEPT",
        reason="ok",
        source="test",
        duration_ms=1,
    )
    content = audit_path.read_text(encoding="utf-8")
    assert secret not in content


def test_log_prompt_hash_deterministic(logger: AuditLogger) -> None:
    h1 = AuditLogger.prompt_hash("hello")
    h2 = AuditLogger.prompt_hash("hello")
    assert h1 == h2


def test_log_prompt_hash_differs_for_different_prompts() -> None:
    assert AuditLogger.prompt_hash("a") != AuditLogger.prompt_hash("b")


def test_log_multiple_records(logger: AuditLogger, audit_path: Path) -> None:
    for i in range(3):
        logger.log(
            prompt=f"prompt {i}",
            route_decision="ACCEPT",
            final_decision="ACCEPT",
            reason="ok",
            source="test",
            duration_ms=i,
        )
    records = _read_records(audit_path)
    assert len(records) == 3
    assert records[0]["duration_ms"] == 0
    assert records[2]["duration_ms"] == 2


def test_log_creates_parent_dirs(tmp_path: Path) -> None:
    deep_path = tmp_path / "a" / "b" / "c" / "audit.jsonl"
    logger = AuditLogger(path=deep_path)
    logger.log(
        prompt="x",
        route_decision="ACCEPT",
        final_decision="ACCEPT",
        reason="ok",
        source="test",
        duration_ms=0,
    )
    assert deep_path.exists()
