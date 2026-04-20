from __future__ import annotations

import pytest

from packages.safety.policy import (
    DECISION_ACCEPT,
    DECISION_BLOCK,
    DECISION_ESCALATE,
    DECISION_SIMULATE,
    DECISION_VERIFY,
    ImpactLevel,
    RiskLevel,
    apply_policy,
)


def test_block_route_returns_block() -> None:
    result = apply_policy(route_decision=DECISION_BLOCK)
    assert result.final_decision == DECISION_BLOCK


def test_accept_low_impact() -> None:
    result = apply_policy(route_decision=DECISION_ACCEPT, metadata={"confidence": 1.0})
    assert result.final_decision == DECISION_ACCEPT
    assert result.risk == RiskLevel.LOW
    assert result.impact == ImpactLevel.LOW


def test_high_impact_not_trusted_escalates() -> None:
    result = apply_policy(
        route_decision=DECISION_ACCEPT,
        metadata={"impact": "HIGH", "confidence": 0.9, "trusted": False},
    )
    assert result.final_decision == DECISION_ESCALATE
    assert result.impact == ImpactLevel.HIGH


def test_high_impact_trusted_accepts() -> None:
    result = apply_policy(
        route_decision=DECISION_ACCEPT,
        metadata={"impact": "HIGH", "confidence": 0.9, "trusted": True},
    )
    assert result.final_decision == DECISION_ACCEPT


def test_high_impact_low_confidence_untrusted_blocks() -> None:
    result = apply_policy(
        route_decision=DECISION_ACCEPT,
        metadata={"impact": "HIGH", "confidence": 0.1, "trusted": False},
    )
    assert result.final_decision == DECISION_BLOCK
    assert result.risk == RiskLevel.CRITICAL


def test_high_impact_trusted_low_confidence_verifies() -> None:
    result = apply_policy(
        route_decision=DECISION_ACCEPT,
        metadata={"impact": "HIGH", "confidence": 0.3, "trusted": True},
    )
    assert result.final_decision == DECISION_VERIFY


def test_destructive_keyword_in_prompt() -> None:
    result = apply_policy(
        route_decision=DECISION_ACCEPT,
        metadata={"prompt": "delete all records", "confidence": 0.9, "trusted": False},
    )
    assert result.final_decision == DECISION_ESCALATE


def test_simulate_route_preserved_low_impact() -> None:
    result = apply_policy(route_decision=DECISION_SIMULATE, metadata={"confidence": 1.0})
    assert result.final_decision == DECISION_SIMULATE


def test_verify_route_preserved_low_impact() -> None:
    result = apply_policy(route_decision=DECISION_VERIFY, metadata={"confidence": 1.0})
    assert result.final_decision == DECISION_VERIFY


def test_confidence_clamped_above_one() -> None:
    result = apply_policy(route_decision=DECISION_ACCEPT, metadata={"confidence": 5.0})
    assert result.final_decision == DECISION_ACCEPT


def test_confidence_clamped_below_zero() -> None:
    result = apply_policy(
        route_decision=DECISION_ACCEPT, metadata={"confidence": -1.0, "impact": "HIGH"}
    )
    assert result.risk in {RiskLevel.CRITICAL, RiskLevel.HIGH}


def test_none_metadata() -> None:
    result = apply_policy(route_decision=DECISION_ACCEPT, metadata=None)
    assert result.final_decision == DECISION_ACCEPT


@pytest.mark.parametrize(
    ("route_decision", "metadata", "expected_final"),
    [
        (DECISION_BLOCK, {}, DECISION_BLOCK),
        (DECISION_ESCALATE, {"confidence": 1.0}, DECISION_ESCALATE),
        (DECISION_ACCEPT, {"confidence": 0.9}, DECISION_ACCEPT),
    ],
)
def test_policy_parametrized(
    route_decision: str, metadata: dict, expected_final: str
) -> None:
    result = apply_policy(route_decision=route_decision, metadata=metadata)
    assert result.final_decision == expected_final
