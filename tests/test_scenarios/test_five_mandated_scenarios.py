"""
tests/test_scenarios/test_five_mandated_scenarios.py

Acceptance-level test suite explicitly enumerating the five claim
scenarios required by the assignment spec, run through the full
``ClaimService`` facade (the same code path the Streamlit UI uses) rather
than the raw graph. This is the suite a reviewer should read first to
confirm end-to-end behavior.

    1. Complete claim, valid documents  -> Auto Approve
    2. Missing required documents       -> Reject
    3. Expired policy                   -> Reject
    4. Suspicious claim (fraud risk)    -> Human Approval
    5. High-value claim                 -> Human Approval
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.services.claim_service import ClaimService
from schemas.enums import ClaimStatus
from schemas.results import HumanReviewOutcome


@pytest.fixture
def claim_service():
    return ClaimService()


def test_scenario_1_complete_valid_claim_is_auto_approved(claim_service, make_claim_input):
    claim_input = make_claim_input(
        claim_amount=45_000,
        max_coverage_amount=1_000_000,
        policy_start_date=date.today() - timedelta(days=900),
        include_documents=True,
    )
    result = claim_service.run_claim(claim_input)

    assert result.is_paused is False
    assert result.state["decision"].status == ClaimStatus.APPROVED


def test_scenario_2_missing_documents_is_rejected(claim_service, make_claim_input):
    claim_input = make_claim_input(include_documents=False)
    result = claim_service.run_claim(claim_input)

    assert result.is_paused is False
    assert result.state["decision"].status == ClaimStatus.REJECTED
    assert "missing" in result.state["decision"].reason.lower() or "document" in result.state["decision"].reason.lower()


def test_scenario_3_expired_policy_is_rejected(claim_service, make_claim_input):
    claim_input = make_claim_input(
        policy_start_date=date.today() - timedelta(days=900),
        policy_end_date=date.today() - timedelta(days=60),
        include_documents=True,
    )
    result = claim_service.run_claim(claim_input)

    assert result.is_paused is False
    assert result.state["decision"].status == ClaimStatus.REJECTED


def test_scenario_4_suspicious_claim_requires_human_approval(claim_service, make_claim_input):
    claim_input = make_claim_input(
        claim_amount=700_000,
        max_coverage_amount=1_000_000,
        policy_start_date=date.today() - timedelta(days=3),
        incident_date=date.today() - timedelta(days=1),
        previous_claims_count=6,
        include_documents=True,
    )
    result = claim_service.run_claim(claim_input)

    assert result.is_paused is True
    assert result.interrupt_payload is not None

    final = claim_service.resume_claim(
        claim_input.claim_id,
        HumanReviewOutcome(approved=True, reviewer_name="SIU Analyst", comments="Cleared after investigation."),
    )
    assert final.state["decision"].status == ClaimStatus.HUMAN_APPROVED


def test_scenario_5_high_value_claim_requires_human_approval(claim_service, make_claim_input):
    claim_input = make_claim_input(
        claim_amount=1_900_000,
        max_coverage_amount=2_000_000,
        policy_start_date=date.today() - timedelta(days=900),
        include_documents=True,
    )
    result = claim_service.run_claim(claim_input)

    assert result.is_paused is True

    final = claim_service.resume_claim(
        claim_input.claim_id,
        HumanReviewOutcome(approved=True, reviewer_name="Senior Underwriter", comments="Approved with documentation."),
    )
    assert final.state["decision"].status == ClaimStatus.HUMAN_APPROVED
