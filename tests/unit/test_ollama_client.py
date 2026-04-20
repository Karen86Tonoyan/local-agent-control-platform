from __future__ import annotations

import json
from http import HTTPStatus
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from packages.llm.ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaHttpError,
    OllamaResponseError,
    OllamaTimeoutError,
)


def _mock_response(payload: dict, status: int = 200) -> MagicMock:
    raw = json.dumps(payload).encode("utf-8")
    mock = MagicMock()
    mock.status = status
    mock.read.return_value = raw
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_generate_success() -> None:
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.1", timeout_seconds=5.0)
    mock_resp = _mock_response({"response": "hello world"})

    with patch("packages.llm.ollama_client.request.urlopen", return_value=mock_resp):
        result = client.generate("say hello")

    assert result == "hello world"


def test_generate_timeout_raises() -> None:
    client = OllamaClient(timeout_seconds=1.0, retries=0)

    with patch("packages.llm.ollama_client.request.urlopen", side_effect=TimeoutError()):
        with pytest.raises(OllamaTimeoutError):
            client.generate("say hello")


def test_generate_http_error_raises() -> None:
    from urllib.error import HTTPError as UrllibHTTPError

    client = OllamaClient(retries=0)
    http_err = UrllibHTTPError(url="", code=500, msg="server error", hdrs=None, fp=None)

    with patch("packages.llm.ollama_client.request.urlopen", side_effect=http_err):
        with pytest.raises(OllamaHttpError):
            client.generate("say hello")


def test_generate_malformed_json_raises() -> None:
    client = OllamaClient(retries=0)
    mock_resp = MagicMock()
    mock_resp.status = HTTPStatus.OK
    mock_resp.read.return_value = b"not json"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("packages.llm.ollama_client.request.urlopen", return_value=mock_resp):
        with pytest.raises(OllamaResponseError):
            client.generate("say hello")


def test_generate_missing_response_key_raises() -> None:
    client = OllamaClient(retries=0)
    mock_resp = _mock_response({"model": "llama3.1"})

    with patch("packages.llm.ollama_client.request.urlopen", return_value=mock_resp):
        with pytest.raises(OllamaResponseError):
            client.generate("say hello")


def test_generate_retries_on_error() -> None:
    client = OllamaClient(retries=1)
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TimeoutError()
        return _mock_response({"response": "ok"})

    with patch("packages.llm.ollama_client.request.urlopen", side_effect=side_effect):
        result = client.generate("say hello")

    assert result == "ok"
    assert call_count == 2


def test_generate_exhausts_retries() -> None:
    client = OllamaClient(retries=1)

    with patch("packages.llm.ollama_client.request.urlopen", side_effect=TimeoutError()):
        with pytest.raises(OllamaTimeoutError):
            client.generate("say hello")
