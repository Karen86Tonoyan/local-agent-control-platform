from __future__ import annotations

from typing import Any


DECISION_ACCEPT = "ACCEPT"
DECISION_VERIFY = "VERIFY"
DECISION_SIMULATE = "SIMULATE"
DECISION_ESCALATE = "ESCALATE"
DECISION_BLOCK = "BLOCK"

VALID_DECISIONS = {
    DECISION_ACCEPT,
    DECISION_VERIFY,
    DECISION_SIMULATE,
    DECISION_ESCALATE,
    DECISION_BLOCK,
}

BLOCK_KEYWORDS = {
    "delete all",
    "drop database",
    "rm -rf",
    "exfiltrate",
    "steal",
}

HIGH_IMPACT_KEYWORDS = {
    "production",
    "deploy",
    "system",
    "admin",
    "payment",
    "invoice",
    "customer data",
}

UNCERTAINTY_KEYWORDS = {
    "maybe",
    "not sure",
    "uncertain",
    "guess",
    "probably",
    "perhaps",
}

SIMULATE_HINT_KEYWORDS = {
    "simulate",
    "dry run",
    "preview",
}

ESCALATE_KEYWORDS = {
    "legal",
    "compliance",
    "security exception",
}


def _text_blob(prompt: str, metadata: dict[str, Any] | None) -> str:
    metadata = metadata or {}
    action = str(metadata.get("action", ""))
    tags = metadata.get("tags", [])
    tags_text = " ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags)
    return f"{prompt} {action} {tags_text}".lower()


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


class AlfaRouter:
    def route(self, prompt: str, metadata: dict[str, Any] | None = None) -> str:
        text = _text_blob(prompt, metadata)

        if _contains_any(text, BLOCK_KEYWORDS):
            return DECISION_BLOCK

        if _contains_any(text, ESCALATE_KEYWORDS):
            return DECISION_ESCALATE

        if _contains_any(text, SIMULATE_HINT_KEYWORDS):
            return DECISION_SIMULATE

        if _contains_any(text, UNCERTAINTY_KEYWORDS):
            return DECISION_VERIFY

        if _contains_any(text, HIGH_IMPACT_KEYWORDS):
            return DECISION_VERIFY

        return DECISION_ACCEPT


def route(prompt: str, metadata: dict[str, Any] | None = None) -> str:
    return AlfaRouter().route(prompt=prompt, metadata=metadata)
