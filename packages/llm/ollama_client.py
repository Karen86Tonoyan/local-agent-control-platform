from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from urllib import error, request


class OllamaError(RuntimeError):
    pass


class OllamaTimeoutError(OllamaError):
    pass


class OllamaHttpError(OllamaError):
    pass


class OllamaResponseError(OllamaError):
    pass


@dataclass(slots=True)
class OllamaClient:
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    timeout_seconds: float = 20.0
    retries: int = 1

    def generate(self, prompt: str) -> str:
        last_error: Exception | None = None

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")

        for attempt in range(self.retries + 1):
            req = request.Request(
                url=f"{self.base_url}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    if resp.status != HTTPStatus.OK:
                        raise OllamaHttpError(f"Unexpected status: {resp.status}")

                    raw = resp.read().decode("utf-8")
                    data = json.loads(raw)
                    response_text = data.get("response")
                    if not isinstance(response_text, str):
                        raise OllamaResponseError("Malformed Ollama response: missing 'response' text")
                    return response_text
            except error.HTTPError as exc:
                last_error = OllamaHttpError(f"HTTP error from Ollama: {exc.code}")
            except TimeoutError as exc:
                last_error = OllamaTimeoutError(f"Timeout after {self.timeout_seconds}s")
            except error.URLError as exc:
                reason = str(exc.reason)
                if "timed out" in reason.lower():
                    last_error = OllamaTimeoutError(f"Timeout after {self.timeout_seconds}s")
                else:
                    last_error = OllamaHttpError(f"Network error: {reason}")
            except json.JSONDecodeError as exc:
                last_error = OllamaResponseError(f"Invalid JSON from Ollama: {exc}")
            except OllamaError as exc:
                last_error = exc

            if attempt >= self.retries:
                break

        if isinstance(last_error, OllamaError):
            raise last_error
        raise OllamaError(f"Ollama request failed after retries: {last_error}")
