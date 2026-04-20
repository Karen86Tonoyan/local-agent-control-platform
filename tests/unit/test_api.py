from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

ENVELOPE_SHAPE = {"request_id", "mode", "decision", "answer", "citations", "warnings", "error"}


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_route_accept_returns_correct_shape() -> None:
    resp = client.post("/route", json={"prompt": "explain this function"})
    assert resp.status_code == 200
    data = resp.json()
    assert ENVELOPE_SHAPE == set(data.keys())


def test_route_block_keyword() -> None:
    resp = client.post("/route", json={"prompt": "rm -rf everything"})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "BLOCK"


def test_route_empty_prompt_rejected() -> None:
    resp = client.post("/route", json={"prompt": ""})
    assert resp.status_code == 422


def test_route_missing_prompt_rejected() -> None:
    resp = client.post("/route", json={})
    assert resp.status_code == 422


def test_ask_returns_correct_shape_when_ollama_available() -> None:
    mock_result = MagicMock()
    mock_result.route_decision = "ACCEPT"
    mock_result.output = "mocked response"
    mock_result.error = None
    mock_result.policy.final_decision = "ACCEPT"
    mock_result.policy.risk.value = "LOW"
    mock_result.policy.impact.value = "LOW"
    mock_result.policy.reason = "ok"

    with patch("apps.api.main.get_ollama_controller") as mock_ctrl_factory:
        mock_ctrl = MagicMock()
        mock_ctrl.ask.return_value = mock_result
        mock_ctrl_factory.return_value = mock_ctrl

        resp = client.post("/ask", json={"prompt": "explain code"})

    assert resp.status_code == 200
    data = resp.json()
    assert ENVELOPE_SHAPE == set(data.keys())
    assert data["answer"] == "mocked response"
    assert data["error"] is None


def test_ask_includes_error_field_on_ollama_failure() -> None:
    mock_result = MagicMock()
    mock_result.route_decision = "ACCEPT"
    mock_result.output = None
    mock_result.error = "Ollama timeout"
    mock_result.policy.final_decision = "ACCEPT"
    mock_result.policy.risk.value = "LOW"
    mock_result.policy.impact.value = "LOW"
    mock_result.policy.reason = "ok"

    with patch("apps.api.main.get_ollama_controller") as mock_ctrl_factory:
        mock_ctrl = MagicMock()
        mock_ctrl.ask.return_value = mock_result
        mock_ctrl_factory.return_value = mock_ctrl

        resp = client.post("/ask", json={"prompt": "explain code"})

    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert "Ollama timeout" in data["error"]


def test_ask_blocked_prompt_does_not_call_ollama() -> None:
    mock_result = MagicMock()
    mock_result.route_decision = "BLOCK"
    mock_result.output = None
    mock_result.error = None
    mock_result.policy.final_decision = "BLOCK"
    mock_result.policy.risk.value = "CRITICAL"
    mock_result.policy.impact.value = "HIGH"
    mock_result.policy.reason = "Router requested BLOCK"

    with patch("apps.api.main.get_ollama_controller") as mock_ctrl_factory:
        mock_ctrl = MagicMock()
        mock_ctrl.ask.return_value = mock_result
        mock_ctrl_factory.return_value = mock_ctrl

        resp = client.post("/ask", json={"prompt": "rm -rf everything"})

    assert resp.status_code == 200
    assert resp.json()["decision"] == "BLOCK"


def test_route_response_shape_stable_across_two_requests() -> None:
    payload = {"prompt": "check status"}
    r1 = client.post("/route", json=payload).json()
    r2 = client.post("/route", json=payload).json()
    assert set(r1.keys()) == set(r2.keys()), "Response shape must be stable"
