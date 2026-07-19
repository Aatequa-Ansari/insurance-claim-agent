"""
tests/test_workflow/test_graph_execution.py

Integration tests for the compiled LangGraph claim-processing workflow.
These exercise the *actual* graph (parallel fan-out/fan-in, conditional
routing, and interrupt-based human-in-the-loop) end to end -- not just
individual agents in isolation.

Covers all five mandated test scenarios from the assignment:
    1. Complete claim, valid documents        -> Auto Approve
    2. Missing required documents              -> Reject
    3. Expired policy                          -> Reject
    4. Suspicious claim (fraud risk)            -> Human Approval
    5. High-value claim                        -> Human Approval

Because these tests run without a configured GOOGLE_API_KEY (no secrets
in CI), every LLM-backed narrative field exercises its deterministic
fallback path -- the numeric/boolean decision logic under test is exactly
the same either way.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from langgraph.types import Command

from langgraph_workflow.graph_builder import build_graph
from schemas.enums import ClaimStatus
from schemas.state import new_claim_state


@pytest.fixture
def compiled_graph():
    """A freshly compiled graph with its own in-memory checkpointer per test."""
    from langgraph.checkpoint.memory import InMemorySaver

    return build_graph().compile(checkpointer=InMemorySaver())


def _run(graph, claim_input):
    config = {"configurable": {"thread_id": claim_input.claim_id}}
    state = new_claim_state(claim_input)
    return graph.invoke(state, config=config), config


def test_scenario_1_complete_claim_auto_approved(compiled_graph, make_claim_input):
    claim_input = make_claim_input(
        claim_amount=50_000,
        max_coverage_amount=1_000_000,
        policy_start_date=date.today() - timedelta(days=800),
        include_documents=True,
        previous_claims_count=0,
    )
    result, _ = _run(compiled_graph, claim_input)

    assert "__interrupt__" not in result
    assert result["decision"].status == ClaimStatus.APPROVED


def test_scenario_2_missing_documents_rejected(compiled_graph, make_claim_input):
    claim_input = make_claim_input(include_documents=False)
    result, _ = _run(compiled_graph, claim_input)

    assert "__interrupt__" not in result
    assert result["decision"].status == ClaimStatus.REJECTED
    assert result["verification_result"].is_complete is False


def test_scenario_3_expired_policy_rejected(compiled_graph, make_claim_input):
    claim_input = make_claim_input(
        policy_start_date=date.today() - timedelta(days=800),
        policy_end_date=date.today() - timedelta(days=30),
        include_documents=True,
    )
    result, _ = _run(compiled_graph, claim_input)

    assert "__interrupt__" not in result
    assert result["decision"].status == ClaimStatus.REJECTED
    assert result["eligibility_result"].is_eligible is False


def test_scenario_4_suspicious_claim_escalates_to_human_review(compiled_graph, make_claim_input):
    claim_input = make_claim_input(
        claim_amount=800_000,
        max_coverage_amount=1_000_000,
        policy_start_date=date.today() - timedelta(days=5),
        incident_date=date.today() - timedelta(days=1),
        previous_claims_count=5,
        include_documents=True,
    )
    result, config = _run(compiled_graph, claim_input)

    assert "__interrupt__" in result
    interrupt_payload = result["__interrupt__"][0].value
    assert "reason" in interrupt_payload

    resumed = compiled_graph.invoke(
        Command(resume={"approved": True, "reviewer_name": "QA Reviewer", "comments": "Verified manually."}),
        config=config,
    )
    assert resumed["decision"].status == ClaimStatus.HUMAN_APPROVED


def test_scenario_5_high_value_claim_escalates_to_human_review(compiled_graph, make_claim_input):
    claim_input = make_claim_input(
        claim_amount=1_800_000,
        max_coverage_amount=2_000_000,
        policy_start_date=date.today() - timedelta(days=800),
        include_documents=True,
        previous_claims_count=0,
    )
    result, config = _run(compiled_graph, claim_input)

    assert "__interrupt__" in result

    resumed = compiled_graph.invoke(
        Command(resume={"approved": False, "reviewer_name": "QA Reviewer", "comments": "Declined after review."}),
        config=config,
    )
    assert resumed["decision"].status == ClaimStatus.HUMAN_REJECTED


def test_parallel_branches_all_populate_state(compiled_graph, make_claim_input):
    """Verifies the three parallel agents all wrote their results before merge."""
    claim_input = make_claim_input()
    result, _ = _run(compiled_graph, claim_input)

    assert result.get("verification_result") is not None
    assert result.get("eligibility_result") is not None
    assert result.get("fraud_result") is not None
    assert result.get("claim_summary") is not None


def test_execution_log_is_populated(compiled_graph, make_claim_input):
    claim_input = make_claim_input()
    result, _ = _run(compiled_graph, claim_input)

    log = result.get("execution_log", [])
    assert len(log) >= 5
    node_names = {entry["node"] for entry in log}
    assert "extract_claim_info" in node_names
    assert "document_verification" in node_names
    assert "decision_engine" in node_names
