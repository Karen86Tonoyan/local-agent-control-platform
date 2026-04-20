from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from packages.router.router import AlfaRouter
from packages.safety.policy import apply_policy
from packages.sensors.activation import ActivationDecision, ActivationGate


class ObservationDecision(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_L2 = "REQUIRE_L2"
    DENY = "DENY"
    BLOCK = "BLOCK"


@dataclass(slots=True)
class ObservationResult:
    decision: ObservationDecision
    action: str
    reason: str
    route_decision: str | None = None
    policy_risk: str | None = None


@dataclass(slots=True)
class ObservationPipeline:
    """
    Orchestrates sensing through L1→L2→L3:

    L1: ActivationGate (wake word filter)
    L2: ActivationGate (PIN / speaker check)
    L3: ALFA Router + Safety Policy

    Sensors never call models directly.
    Pipeline decides whether the observation reaches ALFA.
    """

    gate: ActivationGate
    router: AlfaRouter

    def process(self, action: str, prompt: str, metadata: dict[str, Any] | None = None) -> ObservationResult:
        metadata = metadata or {}

        gate_result = self.gate.request_action(action)

        if gate_result.decision == ActivationDecision.DENY:
            return ObservationResult(
                decision=ObservationDecision.DENY,
                action=action,
                reason=gate_result.reason,
            )

        if gate_result.decision == ActivationDecision.REQUIRE_L2:
            return ObservationResult(
                decision=ObservationDecision.REQUIRE_L2,
                action=action,
                reason=gate_result.reason,
            )

        route_decision = self.router.route(prompt, {**metadata, "action": action})
        policy = apply_policy(route_decision=route_decision, metadata={**metadata, "prompt": prompt})

        if policy.final_decision == "BLOCK":
            return ObservationResult(
                decision=ObservationDecision.BLOCK,
                action=action,
                reason=f"ALFA policy blocked: {policy.reason}",
                route_decision=route_decision,
                policy_risk=policy.risk.value,
            )

        return ObservationResult(
            decision=ObservationDecision.ALLOW,
            action=action,
            reason=policy.reason,
            route_decision=route_decision,
            policy_risk=policy.risk.value,
        )
