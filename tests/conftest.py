"""
tests/conftest.py

Shared pytest fixtures. The most important one is ``stub_llm_service``,
which forces every agent's LLM call to fail deterministically (simulating
"no GOOGLE_API_KEY configured"), so the entire test suite runs offline,
deterministically, and without requiring real Gemini credentials -- while
still exercising every agent's full code path via its documented
fallback behavior.

``MAX_RETRIES`` is forced to ``0`` here (unless already set by the
environment) purely so that the *guaranteed-to-fail* LLM calls exercised
by the test suite don't pay real retry/backoff latency -- this has no
effect on production behavior, where ``core/config/settings.py``'s
default of 3 retries still applies.
"""

from __future__ import annotations

import os

os.environ.setdefault("MAX_RETRIES", "0")

from datetime import date, timedelta

import pytest

from core.services.llm_service import LLMServiceError
from schemas.claim import ClaimDetails, ClaimInput, IncidentDetails, PolicyDetails, UploadedDocument
from schemas.enums import ClaimType, DocumentType


class StubLLMService:
    """A fake LLMService that always raises, forcing agents' deterministic fallback path."""

    def generate_text(self, *args, **kwargs):  # noqa: D102
        raise LLMServiceError("stub: no API key configured for tests")

    def generate_structured(self, *args, **kwargs):  # noqa: D102
        raise LLMServiceError("stub: no API key configured for tests")


@pytest.fixture
def stub_llm_service() -> StubLLMService:
    return StubLLMService()


def _full_document_set() -> list[UploadedDocument]:
    return [
        UploadedDocument(file_name="policy.pdf", document_type=DocumentType.POLICY_DOCUMENT, extracted_text="policy schedule"),
        UploadedDocument(file_name="id.pdf", document_type=DocumentType.IDENTITY_PROOF, extracted_text="passport"),
        UploadedDocument(file_name="police.pdf", document_type=DocumentType.POLICE_REPORT, extracted_text="FIR report"),
        UploadedDocument(file_name="photo.pdf", document_type=DocumentType.INCIDENT_PHOTO, extracted_text="photo evidence"),
        UploadedDocument(file_name="invoice.pdf", document_type=DocumentType.INVOICE_RECEIPT, extracted_text="invoice amount paid"),
    ]


@pytest.fixture
def make_claim_input():
    """Factory fixture for building a valid ``ClaimInput`` with sensible defaults."""

    def _make(
        claim_amount: float = 50_000.0,
        max_coverage_amount: float = 1_000_000.0,
        policy_start_date: date = date.today() - timedelta(days=730),
        policy_end_date: date = date.today() + timedelta(days=365),
        incident_date: date = date.today() - timedelta(days=10),
        waiting_period_days: int = 0,
        previous_claims_count: int = 0,
        claim_type: ClaimType = ClaimType.MOTOR,
        include_documents: bool = True,
        policy_status=None,
    ) -> ClaimInput:
        policy_kwargs = dict(
            policy_number="POL-100234",
            policy_holder_name="Test Claimant",
            policy_start_date=policy_start_date,
            policy_end_date=policy_end_date,
            max_coverage_amount=max_coverage_amount,
            waiting_period_days=waiting_period_days,
        )
        if policy_status is not None:
            policy_kwargs["policy_status"] = policy_status
        policy = PolicyDetails(**policy_kwargs)
        incident = IncidentDetails(
            incident_date=incident_date,
            incident_location="Pune, MH",
            incident_description="Vehicle collision at an intersection causing bumper damage.",
            claim_type=claim_type,
        )
        claim = ClaimDetails(claim_amount=claim_amount, previous_claims_count=previous_claims_count)
        documents = _full_document_set() if include_documents else []
        return ClaimInput(policy=policy, incident=incident, claim=claim, documents=documents)

    return _make
