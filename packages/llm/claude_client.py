from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from urllib import error, request


class ClaudeClientError(RuntimeError):
    pass


class ClaudeConfigurationError(ClaudeClientError):
    pass


class ClaudeHttpError(ClaudeClientError):
    pass


class ClaudeTimeoutError(ClaudeClientError):
    pass


class ClaudeResponseError(ClaudeClientError):
    pass


@dataclass(slots=True)
class ClaudeClient:
    api_key: str
    model: str = "claude-3-5-sonnet-latest"
    timeout_seconds: float = 20.0
    base_url: str = "https://api.anthropic.com"
    anthropic_version: str = "2023-06-01"

    def ask(self, prompt: str, system: str | None = None) -> dict:
        if not self.api_key:
            raise ClaudeConfigurationError("ANTHROPIC_API_KEY is missing")

        payload: dict[str, object] = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/v1/messages",
            data=body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.anthropic_version,
                "content-type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status != HTTPStatus.OK:
                    raise ClaudeHttpError(f"Unexpected Claude status: {resp.status}")

                raw = resp.read().decode("utf-8")
                data = json.loads(raw)

                content = data.get("content")
                if not isinstance(content, list) or not content:
                    raise ClaudeResponseError("Malformed Claude response: missing content list")

                first = content[0]
                if not isinstance(first, dict):
                    raise ClaudeResponseError("Malformed Claude response: content item is not an object")

                answer = first.get("text")
                if not isinstance(answer, str):
                    raise ClaudeResponseError("Malformed Claude response: missing text")

                return {
                    "provider": "claude",
                    "model": str(data.get("model", self.model)),
                    "answer": answer,
                    "id": data.get("id"),
                }
        except error.HTTPError as exc:
            raise ClaudeHttpError(f"Claude HTTP error: {exc.code}") from exc
        except TimeoutError as exc:
            raise ClaudeTimeoutError(f"Claude timeout after {self.timeout_seconds}s") from exc
        except error.URLError as exc:
            reason = str(exc.reason)
            if "timed out" in reason.lower():
                raise ClaudeTimeoutError(f"Claude timeout after {self.timeout_seconds}s") from exc
            raise ClaudeHttpError(f"Claude network error: {reason}") from exc
        except json.JSONDecodeError as exc:
            raise ClaudeResponseError(f"Invalid JSON from Claude: {exc}") from exc