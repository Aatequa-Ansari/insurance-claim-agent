"""
tests/test_services/test_report_service.py

Unit tests for :class:`ReportService` -- ensures JSON and PDF report
generation succeed for a fully-populated claim state.
"""

from __future__ import annotations

import json

from agents.claim_summary_agent import ClaimSummaryAgent
from agents.document_verification_agent import DocumentVerificationAgent
from agents.eligibility_agent import EligibilityAgent
from agents.fraud_detection_agent import FraudDetectionAgent
from core.services.report_service import ReportService
from schemas.results import Decision
from schemas.enums import ClaimStatus
from schemas.state import new_claim_state


def _build_populated_state(make_claim_input, stub_llm_service):
    claim_input = make_claim_input()
    state = new_claim_state(claim_input)

    verification = DocumentVerificationAgent(llm_service=stub_llm_service).evaluate(claim_input)
    eligibility = EligibilityAgent(llm_service=stub_llm_service).evaluate(claim_input)
    fraud = FraudDetectionAgent(llm_service=stub_llm_service).evaluate(claim_input)
    summary = ClaimSummaryAgent(llm_service=stub_llm_service).evaluate(claim_input, verification, eligibility, fraud)

    state["verification_result"] = verification
    state["eligibility_result"] = eligibility
    state["fraud_result"] = fraud
    state["claim_summary"] = summary
    state["decision"] = Decision(status=ClaimStatus.APPROVED, reason="All checks passed.")
    return state


def test_json_report_contains_expected_keys(make_claim_input, stub_llm_service):
    state = _build_populated_state(make_claim_input, stub_llm_service)
    service = ReportService(reports_dir="/tmp/test_reports")

    raw = service.build_json_report(state)
    parsed = json.loads(raw)

    assert parsed["claim_id"] == state["claim_input"].claim_id
    assert parsed["decision"]["status"] == "APPROVED"
    assert parsed["verification_result"] is not None
    assert parsed["fraud_result"] is not None


def test_pdf_report_generates_nonempty_bytes(make_claim_input, stub_llm_service):
    state = _build_populated_state(make_claim_input, stub_llm_service)
    service = ReportService(reports_dir="/tmp/test_reports")

    pdf_bytes = service.build_pdf_report(state)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes[:4] == b"%PDF"
