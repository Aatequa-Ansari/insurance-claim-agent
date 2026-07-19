"""
tests/test_agents/test_fraud_detection_agent.py

Unit tests for :class:`FraudDetectionAgent`'s deterministic scoring heuristics.
"""

from __future__ import annotations

from datetime import date, timedelta

from agents.fraud_detection_agent import FraudDetectionAgent
from schemas.enums import FraudRisk


def test_low_risk_claim_scores_low(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(
        claim_amount=20_000,
        max_coverage_amount=1_000_000,
        policy_start_date=date.today() - timedelta(days=800),
        previous_claims_count=0,
    )
    agent = FraudDetectionAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.fraud_risk == FraudRisk.LOW
    assert result.risk_score < 40


def test_fresh_policy_and_frequent_claims_raise_risk(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(
        claim_amount=800_000,
        max_coverage_amount=1_000_000,
        policy_start_date=date.today() - timedelta(days=5),
        previous_claims_count=5,
    )
    agent = FraudDetectionAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.fraud_risk in (FraudRisk.MEDIUM, FraudRisk.HIGH)
    assert result.risk_score >= 40
    assert result.is_duplicate_suspected is True


def test_risk_score_bounded_at_100(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(
        claim_amount=990_000,
        max_coverage_amount=1_000_000,
        policy_start_date=date.today() - timedelta(days=1),
        previous_claims_count=10,
    )
    agent = FraudDetectionAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert 0 <= result.risk_score <= 100
