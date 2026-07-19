"""
tests/test_agents/test_document_verification_agent.py

Unit tests for :class:`DocumentVerificationAgent`, using the stubbed LLM
service so results are fully deterministic.
"""

from __future__ import annotations

from agents.document_verification_agent import DocumentVerificationAgent
from schemas.enums import ClaimType, DocumentType


def test_complete_documents_marks_claim_complete(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(include_documents=True, claim_type=ClaimType.MOTOR)
    agent = DocumentVerificationAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.is_complete is True
    assert result.missing_documents == []
    assert result.completeness_score == 100.0


def test_missing_documents_are_detected(make_claim_input, stub_llm_service):
    claim_input = make_claim_input(include_documents=False, claim_type=ClaimType.MOTOR)
    agent = DocumentVerificationAgent(llm_service=stub_llm_service)

    result = agent.evaluate(claim_input)

    assert result.is_complete is False
    assert DocumentType.POLICY_DOCUMENT in result.missing_documents
    assert result.completeness_score == 0.0


def test_required_documents_vary_by_claim_type(make_claim_input, stub_llm_service):
    agent = DocumentVerificationAgent(llm_service=stub_llm_service)

    motor_claim = make_claim_input(include_documents=False, claim_type=ClaimType.MOTOR)
    health_claim = make_claim_input(include_documents=False, claim_type=ClaimType.HEALTH)

    motor_result = agent.evaluate(motor_claim)
    health_result = agent.evaluate(health_claim)

    assert DocumentType.POLICE_REPORT in motor_result.required_documents
    assert DocumentType.MEDICAL_REPORT in health_result.required_documents
    assert DocumentType.POLICE_REPORT not in health_result.required_documents
