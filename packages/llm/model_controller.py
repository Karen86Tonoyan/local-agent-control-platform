from __future__ import annotations

from dataclasses import dataclass

from packages.llm.claude_client import ClaudeClient, ClaudeClientError
from packages.llm.ollama_client import OllamaClient, OllamaError
from packages.llm.openai_client import OpenAIClient, OpenAIClientError


ROUTE_BLOCK = "BLOCK"


@dataclass(slots=True)
class ModelController:
    ollama: OllamaClient
    openai: OpenAIClient | None = None
    claude: ClaudeClient | None = None

    def ask(self, prompt: str, metadata: dict | None = None) -> dict:
        metadata = metadata or {}

        task_type = str(metadata.get("task_type", "general")).lower()
        privacy_required = bool(metadata.get("privacy_required", False))
        risk_level = str(metadata.get("risk_level", "LOW")).upper()
        route_decision = str(metadata.get("route_decision", "ACCEPT")).upper()
        preferred_provider = str(metadata.get("preferred_provider", "")).lower()
        cloud_unavailable = bool(metadata.get("cloud_unavailable", False))
        high_impact = bool(metadata.get("high_impact", False))
        system_prompt = metadata.get("system")
        system = str(system_prompt) if isinstance(system_prompt, str) else None

        if route_decision == ROUTE_BLOCK:
            return {
                "provider": "ollama",
                "model": self.ollama.model,
                "mode": "BLOCKED",
                "answer": "Request blocked by ALFA policy.",
                "reason": "Route decision is BLOCK; model generation disabled",
            }

        provider, mode, reason, openai_mode = self._select_provider(
            task_type=task_type,
            privacy_required=privacy_required,
            risk_level=risk_level,
            preferred_provider=preferred_provider,
            cloud_unavailable=cloud_unavailable,
            high_impact=high_impact,
        )

        if provider == "openai":
            result = self._ask_openai(prompt=prompt, system=system, mode=openai_mode)
            if result is None:
                fallback = self._ask_ollama(prompt=prompt)
                fallback["mode"] = "FAST_LOCAL"
                fallback["reason"] = f"{reason}; OpenAI unavailable, fallback to Ollama"
                return fallback
            result["mode"] = mode
            result["reason"] = reason
            return result

        if provider == "claude":
            result = self._ask_claude(prompt=prompt, system=system)
            if result is None:
                fallback = self._ask_ollama(prompt=prompt)
                fallback["mode"] = "FAST_LOCAL"
                fallback["reason"] = f"{reason}; Claude unavailable, fallback to Ollama"
                return fallback
            result["mode"] = mode
            result["reason"] = reason
            return result

        result = self._ask_ollama(prompt=prompt)
        result["mode"] = mode
        result["reason"] = reason
        return result

    def _select_provider(
        self,
        *,
        task_type: str,
        privacy_required: bool,
        risk_level: str,
        preferred_provider: str,
        cloud_unavailable: bool,
        high_impact: bool,
    ) -> tuple[str, str, str, str]:
        if privacy_required:
            return "ollama", "OFFLINE_ONLY", "Privacy required: local provider only", "gpt"

        if cloud_unavailable:
            return "ollama", "FAST_LOCAL", "Cloud unavailable: fallback to local provider", "gpt"

        if preferred_provider in {"ollama", "openai", "claude"}:
            openai_mode = "codex" if task_type in {"code", "execution"} else "gpt"
            return preferred_provider, "EXECUTION", "Preferred provider selected by metadata", openai_mode

        if task_type in {"review", "safety"} or high_impact or risk_level in {"HIGH", "CRITICAL"}:
            return "claude", "SAFETY_REVIEW", "Review/safety/high-impact task routed to Claude", "gpt"

        if task_type in {"code", "execution"}:
            return "openai", "EXECUTION", "Code/execution task routed to OpenAI Codex mode", "codex"

        return "ollama", "FAST_LOCAL", "Default local-first policy", "gpt"

    def _ask_openai(self, *, prompt: str, system: str | None, mode: str) -> dict | None:
        if self.openai is None:
            return None
        try:
            return self.openai.ask(prompt=prompt, system=system, mode=mode)
        except OpenAIClientError:
            return None

    def _ask_claude(self, *, prompt: str, system: str | None) -> dict | None:
        if self.claude is None:
            return None
        try:
            return self.claude.ask(prompt=prompt, system=system)
        except ClaudeClientError:
            return None

    def _ask_ollama(self, *, prompt: str) -> dict:
        try:
            answer = self.ollama.generate(prompt)
            return {
                "provider": "ollama",
                "model": self.ollama.model,
                "answer": answer,
            }
        except OllamaError as exc:
            return {
                "provider": "ollama",
                "model": self.ollama.model,
                "answer": "",
                "reason": f"Ollama error: {exc}",
            }