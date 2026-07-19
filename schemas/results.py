"""
schemas/results.py

Structured output models produced by each agent. These double as the
LangChain / LangGraph "output parser" targets: every LLM-backed agent is
instructed (via prompt + parser) to return JSON matching one of these
schemas, which is then validated by Pydantic before being written into
the shared graph state.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from schemas.enums import ClaimStatus, DocumentType, FraudRisk


class DocumentCheckItem(BaseModel):
    """Result of checking a single required document category."""

    document_type: DocumentType
    is_present: bool
    is_valid: bool = True
    notes: str = ""


class VerificationResult(BaseModel):
    """Output of the Document Verification Agent."""

    is_complete: bool
    required_documents: list[DocumentType]
    missing_documents: list[DocumentType] = Field(default_factory=list)
    document_checks: list[DocumentCheckItem] = Field(default_factory=list)
    completeness_score: float = Field(..., ge=0, le=100)
    summary: str = ""


class EligibilityResult(BaseModel):
    """Output of the Eligibility Check Agent."""

    is_eligible: bool
    policy_active: bool
    within_coverage_period: bool
    waiting_period_satisfied: bool
    claim_type_covered: bool
    within_max_coverage: bool
    ineligibility_reasons: list[str] = Field(default_factory=list)
    summary: str = ""


class FraudResult(BaseModel):
    """Output of the Fraud Detection Agent."""

    fraud_risk: FraudRisk
    risk_score: float = Field(..., ge=0, le=100)
    suspicious_patterns: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    is_duplicate_suspected: bool = False
    summary: str = ""


class ClaimSummary(BaseModel):
    """Output of the Claim Summary Agent."""

    executive_summary: str
    evidence_summary: str
    business_justification: str
    supporting_information: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Decision(BaseModel):
    """Final (or interim) decision produced by the Decision Engine node."""

    status: ClaimStatus
    reason: str
    requires_human_review: bool = False
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    decided_by: str = "SYSTEM"  # "SYSTEM" or reviewer identifier


class HumanReviewOutcome(BaseModel):
    """Captures a human reviewer's decision during Human-in-the-Loop."""

    approved: bool
    reviewer_name: str = "Reviewer"
    comments: str = ""
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
