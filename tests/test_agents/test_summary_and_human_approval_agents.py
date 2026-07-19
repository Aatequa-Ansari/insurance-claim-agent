"""
tests/test_agents/test_summary_and_human_approval_agents.py

Unit tests for :class:`ClaimSummaryAgent` (fallback path) and
:class:`HumanApprovalAgent` (escalation rules + finalize logic).
"""

from __future__ import annotations

from agents.claim_summary_agent import ClaimSummaryAgent
from agents.document_verification_agent import DocumentVerificationAgent
from agents.eligibility_agent import EligibilityAgent
from agents.fraud_detection_agent import FraudDetectionAgent
from agents.human_approval_agent import HumanApprovalAgent
from schemas.enums import ClaimStatus
from schemas.results import HumanReviewOutcome


def _evaluate_all(claim_input, stub_llm_service):
    verification = DocumentVerificationAgent(llm_service=stub_llm_service).evaluate(claim_input)
    eligibility = EligibilityAgent(llm_service=stub_llm_service).evaluate(claim_input)
    fraud = FraudDetectionAgent(llm_service=stub_llm_service).evaluate(claim_input)
    return verification, eligibility, fraud


def test_claim_summary_fallback_produces_valid_summary(make_claim_input, stub_llm_service):
    claim_input = make_claim_input()
    verification, eligibility, fraud = _evaluate_all(claim_input, stub_llm_service)

    summary_agent = ClaimSummaryAgent(llm_service=stub_llm_service)
    summary = summary_agent.evaluate(claim_input, verification, eligibility, fraud)

    assert summary.executive_summary
    assert summary.evidence_summary
    assert summary.business_justification
    assert len(summary.supporting_information) > 0


def test_human_approval_no_escalation_for_low_risk_claim(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(claim_amount=50_000, max_coverage_amount=1_000_000, previous_claims_count=0)
    verification, eligibility, fraud = _evaluate_all(claim_input, stub_llm_service)

    human_agent = HumanApprovalAgent()
    should_escalate, _ = human_agent.requires_escalation(claim_input, verification, eligibility, fraud)

    assert should_escalate is False


def test_human_approval_escalates_high_value_claim(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(claim_amount=900_000, max_coverage_amount=1_000_000)
    verification, eligibility, fraud = _evaluate_all(claim_input, stub_llm_service)

    human_agent = HumanApprovalAgent()
    should_escalate, reason = human_agent.requires_escalation(claim_input, verification, eligibility, fraud)

    assert should_escalate is True
    assert reason


def test_human_approval_finalize_approved():
    outcome = HumanReviewOutcome(approved=True, reviewer_name="Alice", comments="Looks fine.")
    decision = HumanApprovalAgent.finalize(outcome)
    assert decision.status == ClaimStatus.HUMAN_APPROVED
    assert "Alice" in decision.reason


def test_human_approval_finalize_rejected():
    outcome = HumanReviewOutcome(approved=False, reviewer_name="Bob", comments="Too risky.")
    decision = HumanApprovalAgent.finalize(outcome)
    assert decision.status == ClaimStatus.HUMAN_REJECTED
    assert "Bob" in decision.reason
