"""
tests/test_validation/test_schemas.py

Validation tests for the Pydantic schema layer (schemas/claim.py,
schemas/results.py). These guard the "boundary contract" between the UI
and the workflow -- if a rule here breaks, invalid data could otherwise
silently flow into the LangGraph state.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from schemas.claim import ClaimDetails, ClaimInput, IncidentDetails, PolicyDetails
from schemas.enums import ClaimType


def test_policy_end_date_must_be_after_start_date():
    with pytest.raises(ValidationError):
        PolicyDetails(
            policy_number="POL-1",
            policy_holder_name="Jane Doe",
            policy_start_date=date(2026, 1, 1),
            policy_end_date=date(2025, 1, 1),
            max_coverage_amount=100_000,
        )


def test_policy_is_expired_property():
    policy = PolicyDetails(
        policy_number="POL-1",
        policy_holder_name="Jane Doe",
        policy_start_date=date.today() - timedelta(days=800),
        policy_end_date=date.today() - timedelta(days=30),
        max_coverage_amount=100_000,
    )
    assert policy.is_expired is True


def test_incident_date_cannot_be_in_the_future():
    with pytest.raises(ValidationError):
        IncidentDetails(
            incident_date=date.today() + timedelta(days=1),
            incident_location="Pune",
            incident_description="Some incident description that is long enough.",
            claim_type=ClaimType.MOTOR,
        )


def test_claim_amount_must_be_positive():
    with pytest.raises(ValidationError):
        ClaimDetails(claim_amount=-100)


def test_claim_input_high_value_fraction(make_claim_input):
    claim_input: ClaimInput = make_claim_input(claim_amount=250_000, max_coverage_amount=1_000_000)
    assert claim_input.high_value_threshold_fraction() == pytest.approx(0.25)


def test_claim_id_auto_generated(make_claim_input):
    claim_input: ClaimInput = make_claim_input()
    assert claim_input.claim_id.startswith("CLM-")
