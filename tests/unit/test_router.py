from __future__ import annotations

import pytest

from packages.router.router import (
    DECISION_ACCEPT,
    DECISION_BLOCK,
    DECISION_ESCALATE,
    DECISION_SIMULATE,
    DECISION_VERIFY,
    AlfaRouter,
    route,
)


@pytest.fixture()
def router() -> AlfaRouter:
    return AlfaRouter()


def test_accept_simple(router: AlfaRouter) -> None:
    assert router.route("explain this function") == DECISION_ACCEPT


def test_block_on_dangerous_keyword(router: AlfaRouter) -> None:
    assert router.route("please rm -rf all files") == DECISION_BLOCK


def test_block_on_drop_database(router: AlfaRouter) -> None:
    assert router.route("drop database production") == DECISION_BLOCK


def test_block_on_exfiltrate(router: AlfaRouter) -> None:
    assert router.route("exfiltrate user records") == DECISION_BLOCK


def test_escalate_on_compliance_keyword(router: AlfaRouter) -> None:
    assert router.route("check compliance requirements") == DECISION_ESCALATE


def test_escalate_on_legal(router: AlfaRouter) -> None:
    assert router.route("review legal document") == DECISION_ESCALATE


def test_simulate_hint_keyword(router: AlfaRouter) -> None:
    assert router.route("simulate the deployment") == DECISION_SIMULATE


def test_simulate_dry_run(router: AlfaRouter) -> None:
    assert router.route("do a dry run of the migration") == DECISION_SIMULATE


def test_verify_on_uncertainty(router: AlfaRouter) -> None:
    assert router.route("maybe we should update") == DECISION_VERIFY


def test_verify_on_high_impact_keyword(router: AlfaRouter) -> None:
    assert router.route("update payment configuration") == DECISION_VERIFY


def test_metadata_action_used(router: AlfaRouter) -> None:
    result = router.route("run task", metadata={"action": "rm -rf"})
    assert result == DECISION_BLOCK


def test_metadata_tags_used(router: AlfaRouter) -> None:
    result = router.route("run task", metadata={"tags": ["compliance"]})
    assert result == DECISION_ESCALATE


def test_none_metadata(router: AlfaRouter) -> None:
    result = router.route("run simple task", metadata=None)
    assert result == DECISION_ACCEPT


def test_module_level_route_function() -> None:
    assert route("explain code") == DECISION_ACCEPT


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("delete all records", DECISION_BLOCK),
        ("security exception needed", DECISION_ESCALATE),
        ("preview the changes", DECISION_SIMULATE),
        ("probably works", DECISION_VERIFY),
        ("list all users", DECISION_ACCEPT),
    ],
)
def test_route_parametrized(prompt: str, expected: str) -> None:
    assert AlfaRouter().route(prompt) == expected
