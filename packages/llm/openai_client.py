from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from urllib import error, request


class OpenAIClientError(RuntimeError):
    pass


class OpenAIConfigurationError(OpenAIClientError):
    pass


class OpenAIHttpError(OpenAIClientError):
    pass


class OpenAITimeoutError(OpenAIClientError):
    pass


class OpenAIResponseError(OpenAIClientError):
    pass


@dataclass(slots=True)
class OpenAIClient:
    api_key: str
    gpt_model: str = "gpt-4o-mini"
    codex_model: str = "gpt-5.1-codex"
    timeout_seconds: float = 20.0
    base_url: str = "https://api.openai.com"

    def ask(self, prompt: str, system: str | None = None, mode: str = "gpt") -> dict:
        if not self.api_key:
            raise OpenAIConfigurationError("OPENAI_API_KEY is missing")

        selected_mode = mode.lower().strip()
        if selected_mode not in {"gpt", "codex"}:
            raise OpenAIConfigurationError("OpenAI mode must be 'gpt' or 'codex'")

        model = self.codex_model if selected_mode == "codex" else self.gpt_model

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
        }
        body = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url=f"{self.base_url}/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status != HTTPStatus.OK:
                    raise OpenAIHttpError(f"Unexpected OpenAI status: {resp.status}")

                raw = resp.read().decode("utf-8")
                data = json.loads(raw)

                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    raise OpenAIResponseError("Malformed OpenAI response: missing choices")

                message = choices[0].get("message", {})
                answer = message.get("content")
                if not isinstance(answer, str):
                    raise OpenAIResponseError("Malformed OpenAI response: missing content")

                return {
                    "provider": "openai",
                    "model": str(data.get("model", model)),
                    "mode": selected_mode,
                    "answer": answer,
                    "id": data.get("id"),
                }
        except error.HTTPError as exc:
            raise OpenAIHttpError(f"OpenAI HTTP error: {exc.code}") from exc
        except TimeoutError as exc:
            raise OpenAITimeoutError(f"OpenAI timeout after {self.timeout_seconds}s") from exc
        except error.URLError as exc:
            reason = str(exc.reason)
            if "timed out" in reason.lower():
                raise OpenAITimeoutError(f"OpenAI timeout after {self.timeout_seconds}s") from exc
            raise OpenAIHttpError(f"OpenAI network error: {reason}") from exc
        except json.JSONDecodeError as exc:
            raise OpenAIResponseError(f"Invalid JSON from OpenAI: {exc}") from exc