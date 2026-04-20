from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

ENVELOPE_KEYS = {"request_id", "mode", "decision", "answer", "citations", "warnings", "error"}


def _assert_envelope(data: dict) -> None:
    assert ENVELOPE_KEYS == set(data.keys()), f"Unexpected keys: {set(data.keys()) ^ ENVELOPE_KEYS}"
    assert isinstance(data["request_id"], str) and data["request_id"]
    assert isinstance(data["mode"], str) and data["mode"]
    assert isinstance(data["decision"], str) and data["decision"]
    assert isinstance(data["citations"], list)
    assert isinstance(data["warnings"], list)
    # error must always be present (null or string)
    assert "error" in data


def test_health_still_works() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_route_returns_envelope() -> None:
    resp = client.post("/route", json={"prompt": "explain this function"})
    assert resp.status_code == 200
    _assert_envelope(resp.json())


def test_route_envelope_mode_is_route() -> None:
    resp = client.post("/route", json={"prompt": "explain this function"})
    assert resp.json()["mode"] == "route"


def test_route_decision_is_valid() -> None:
    from packages.core.domain import RouteDecision
    valid = {d.value for d in RouteDecision}
    resp = client.post("/route", json={"prompt": "explain this function"})
    assert resp.json()["decision"] in valid


def test_route_block_decision_in_envelope() -> None:
    resp = client.post("/route", json={"prompt": "rm -rf everything"})
    assert resp.status_code == 200
    data = resp.json()
    _assert_envelope(data)
    assert data["decision"] == "BLOCK"


def test_route_answer_is_none() -> None:
    resp = client.post("/route", json={"prompt": "explain code"})
    assert resp.json()["answer"] is None


def test_route_error_is_null_on_success() -> None:
    resp = client.post("/route", json={"prompt": "explain code"})
    assert resp.json()["error"] is None


def test_route_request_id_is_unique() -> None:
    r1 = client.post("/route", json={"prompt": "explain code"}).json()
    r2 = client.post("/route", json={"prompt": "explain code"}).json()
    assert r1["request_id"] != r2["request_id"]


def test_route_shape_stable_across_calls() -> None:
    r1 = client.post("/route", json={"prompt": "check status"}).json()
    r2 = client.post("/route", json={"prompt": "check status"}).json()
    assert set(r1.keys()) == set(r2.keys())


def test_ask_returns_envelope() -> None:
    from unittest.mock import MagicMock, patch

    mock_result = MagicMock()
    mock_result.route_decision = "ACCEPT"
    mock_result.output = "answer text"
    mock_result.error = None
    mock_result.policy.final_decision = "ACCEPT"
    mock_result.policy.risk.value = "LOW"
    mock_result.policy.impact.value = "LOW"
    mock_result.policy.reason = "ok"

    with patch("apps.api.main.get_ollama_controller") as mock_factory:
        mock_ctrl = MagicMock()
        mock_ctrl.ask.return_value = mock_result
        mock_factory.return_value = mock_ctrl
        resp = client.post("/ask", json={"prompt": "explain code"})

    assert resp.status_code == 200
    _assert_envelope(resp.json())


def test_ask_envelope_mode_is_ask() -> None:
    from unittest.mock import MagicMock, patch

    mock_result = MagicMock()
    mock_result.route_decision = "ACCEPT"
    mock_result.output = "text"
    mock_result.error = None
    mock_result.policy.final_decision = "ACCEPT"
    mock_result.policy.risk.value = "LOW"
    mock_result.policy.impact.value = "LOW"
    mock_result.policy.reason = "ok"

    with patch("apps.api.main.get_ollama_controller") as mock_factory:
        mock_ctrl = MagicMock()
        mock_ctrl.ask.return_value = mock_result
        mock_factory.return_value = mock_ctrl
        resp = client.post("/ask", json={"prompt": "explain code"})

    assert resp.json()["mode"] == "ask"


def test_ask_error_in_envelope_on_ollama_failure() -> None:
    from unittest.mock import MagicMock, patch

    mock_result = MagicMock()
    mock_result.route_decision = "ACCEPT"
    mock_result.output = None
    mock_result.error = "Timeout"
    mock_result.policy.final_decision = "ACCEPT"
    mock_result.policy.risk.value = "LOW"
    mock_result.policy.impact.value = "LOW"
    mock_result.policy.reason = "ok"

    with patch("apps.api.main.get_ollama_controller") as mock_factory:
        mock_ctrl = MagicMock()
        mock_ctrl.ask.return_value = mock_result
        mock_factory.return_value = mock_ctrl
        resp = client.post("/ask", json={"prompt": "explain code"})

    data = resp.json()
    _assert_envelope(data)
    assert data["error"] == "Timeout"
    assert any("Timeout" in w for w in data["warnings"])


def test_ask_empty_prompt_rejected() -> None:
    resp = client.post("/ask", json={"prompt": ""})
    assert resp.status_code == 422
