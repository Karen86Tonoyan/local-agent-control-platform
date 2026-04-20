from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ImpactLevel(StrEnum):
    LOW = "LOW"
    HIGH = "HIGH"


@dataclass(slots=True)
class PolicyResult:
    final_decision: str
    risk: RiskLevel
    impact: ImpactLevel
    reason: str


DECISION_ACCEPT = "ACCEPT"
DECISION_VERIFY = "VERIFY"
DECISION_SIMULATE = "SIMULATE"
DECISION_ESCALATE = "ESCALATE"
DECISION_BLOCK = "BLOCK"

DESTRUCTIVE_ACTION_KEYWORDS = {
    "destructive",
    "system",
    "admin",
    "payment",
    "delete",
    "drop",
    "shutdown",
    "privileged",
}


def _extract_confidence(metadata: dict[str, Any]) -> float:
    value = metadata.get("confidence", 1.0)
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 1.0
    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return confidence


def _is_high_impact(metadata: dict[str, Any], prompt: str) -> bool:
    explicit_impact = str(metadata.get("impact", "")).upper()
    if explicit_impact == ImpactLevel.HIGH.value:
        return True

    action = str(metadata.get("action", "")).lower()
    prompt_lower = prompt.lower()
    return any(token in action or token in prompt_lower for token in DESTRUCTIVE_ACTION_KEYWORDS)


def _risk_level(high_impact: bool, confidence: float) -> RiskLevel:
    if high_impact and confidence < 0.35:
        return RiskLevel.CRITICAL
    if high_impact and confidence < 0.6:
        return RiskLevel.HIGH
    if high_impact:
        return RiskLevel.MEDIUM
    if confidence < 0.35:
        return RiskLevel.HIGH
    if confidence < 0.6:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def apply_policy(route_decision: str, metadata: dict[str, Any] | None = None) -> PolicyResult:
    metadata = metadata or {}
    prompt = str(metadata.get("prompt", ""))
    trusted = bool(metadata.get("trusted", False))
    confidence = _extract_confidence(metadata)
    high_impact = _is_high_impact(metadata, prompt)

    risk = _risk_level(high_impact=high_impact, confidence=confidence)
    impact = ImpactLevel.HIGH if high_impact else ImpactLevel.LOW

    if route_decision == DECISION_BLOCK:
        return PolicyResult(
            final_decision=DECISION_BLOCK,
            risk=risk,
            impact=impact,
            reason="Router requested BLOCK",
        )

    if high_impact and not trusted:
        if confidence < 0.5:
            return PolicyResult(
                final_decision=DECISION_BLOCK,
                risk=RiskLevel.CRITICAL,
                impact=ImpactLevel.HIGH,
                reason="High-impact destructive action with low confidence and no trust",
            )

        if route_decision in {DECISION_ACCEPT, DECISION_VERIFY, DECISION_SIMULATE}:
            return PolicyResult(
                final_decision=DECISION_ESCALATE,
                risk=max(risk, RiskLevel.HIGH, key=lambda level: list(RiskLevel).index(level)),
                impact=ImpactLevel.HIGH,
                reason="High-impact destructive action requires escalation unless explicitly trusted",
            )

    if high_impact and confidence < 0.6 and route_decision == DECISION_ACCEPT:
        return PolicyResult(
            final_decision=DECISION_VERIFY,
            risk=risk,
            impact=ImpactLevel.HIGH,
            reason="Low confidence + high impact requires VERIFY or stronger",
        )

    return PolicyResult(
        final_decision=route_decision,
        risk=risk,
        impact=impact,
        reason="Policy accepted router decision",
    )
