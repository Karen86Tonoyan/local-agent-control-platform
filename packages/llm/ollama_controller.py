from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from packages.router.router import AlfaRouter
from packages.safety.policy import PolicyResult, apply_policy  # noqa: F401

from .ollama_client import OllamaClient, OllamaError


@dataclass(slots=True)
class AskResult:
    route_decision: str
    policy: PolicyResult
    output: str | None
    error: str | None


@dataclass(slots=True)
class OllamaController:
    router: AlfaRouter
    client: OllamaClient

    def ask(self, prompt: str, metadata: dict[str, Any] | None = None) -> AskResult:
        metadata = metadata or {}

        route_decision = self.router.route(prompt, metadata)
        policy = apply_policy(route_decision=route_decision, metadata={**metadata, "prompt": prompt})

        output: str | None = None
        error_text: str | None = None

        if policy.final_decision in {"ACCEPT", "SIMULATE"}:
            try:
                output = self.client.generate(prompt)
            except OllamaError as exc:
                error_text = str(exc)

        return AskResult(
            route_decision=route_decision,
            policy=policy,
            output=output,
            error=error_text,
        )