"""
tests/test_agents/test_eligibility_agent.py

Unit tests for :class:`EligibilityAgent`.
"""

from __future__ import annotations

from datetime import date, timedelta

from agents.eligibility_agent import EligibilityAgent


def test_active_policy_within_period_is_eligible(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(
        policy_start_date=date.today() - timedelta(days=400),
        policy_end_date=date.today() + timedelta(days=400),
        incident_date=date.today() - timedelta(days=5),
        claim_amount=50_000,
        max_coverage_amount=1_000_000,
    )
    agent = EligibilityAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.is_eligible is True
    assert result.policy_active is True
    assert result.ineligibility_reasons == []


def test_expired_policy_is_not_eligible(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(
        policy_start_date=date.today() - timedelta(days=800),
        policy_end_date=date.today() - timedelta(days=30),
        incident_date=date.today() - timedelta(days=5),
    )
    agent = EligibilityAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.is_eligible is False
    assert result.policy_active is False
    assert len(result.ineligibility_reasons) > 0


def test_claim_exceeding_max_coverage_is_not_eligible(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(claim_amount=2_000_000, max_coverage_amount=1_000_000)
    agent = EligibilityAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.is_eligible is False
    assert result.within_max_coverage is False


def test_waiting_period_not_satisfied(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(
        policy_start_date=date.today() - timedelta(days=5),
        incident_date=date.today() - timedelta(days=1),
        waiting_period_days=30,
    )
    agent = EligibilityAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.waiting_period_satisfied is False
    assert result.is_eligible is False
