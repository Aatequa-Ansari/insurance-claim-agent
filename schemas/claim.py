"""
schemas/claim.py

Pydantic models describing the *input* side of a claim: the policy being
claimed against, the incident that occurred, the claim itself, and any
uploaded supporting documents.

These models are the contract between the Streamlit UI (claim_form.py /
upload_widget.py) and the backend ClaimService. Validation happens here,
once, at the boundary -- downstream agents can trust the shape of the data.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from schemas.enums import ClaimType, DocumentType, PolicyStatus


class PolicyDetails(BaseModel):
    """Details of the insurance policy the claim is filed against."""

    policy_number: str = Field(..., min_length=3, description="Unique policy identifier")
    policy_holder_name: str = Field(..., min_length=2)
    policy_status: PolicyStatus = Field(default=PolicyStatus.ACTIVE)
    policy_start_date: date
    policy_end_date: date
    max_coverage_amount: float = Field(..., gt=0, description="Maximum payable coverage")
    waiting_period_days: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_date_range(self) -> "PolicyDetails":
        if self.policy_end_date <= self.policy_start_date:
            raise ValueError("policy_end_date must be after policy_start_date")
        return self

    @property
    def is_expired(self) -> bool:
        """True if the policy end date has already passed."""
        return self.policy_end_date < date.today()

    @property
    def policy_age_days(self) -> int:
        """Number of days elapsed since the policy started."""
        return (date.today() - self.policy_start_date).days


class IncidentDetails(BaseModel):
    """Details describing the incident that triggered the claim."""

    incident_date: date
    incident_location: str = Field(..., min_length=2)
    incident_description: str = Field(..., min_length=10, max_length=5000)
    claim_type: ClaimType

    @field_validator("incident_date")
    @classmethod
    def incident_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("incident_date cannot be in the future")
        return v


class UploadedDocument(BaseModel):
    """Metadata + extracted text for a single uploaded supporting document."""

    document_id: str = Field(default_factory=lambda: str(uuid4()))
    file_name: str
    document_type: DocumentType = DocumentType.OTHER
    extracted_text: str = ""
    page_count: int = 0
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    size_bytes: int = 0


class ClaimDetails(BaseModel):
    """The financial / procedural facts of the claim itself."""

    claim_amount: float = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    previous_claims_count: int = Field(default=0, ge=0, description="Prior claims on this policy")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class ClaimInput(BaseModel):
    """Top-level container combining policy, incident, and claim data.

    This is the single object constructed from the Streamlit claim form and
    passed into the LangGraph workflow as the seed of ``ClaimState``.
    """

    claim_id: str = Field(default_factory=lambda: f"CLM-{uuid4().hex[:8].upper()}")
    policy: PolicyDetails
    incident: IncidentDetails
    claim: ClaimDetails
    documents: list[UploadedDocument] = Field(default_factory=list)

    def high_value_threshold_fraction(self) -> float:
        """Ratio of claim amount to max coverage -- used by fraud/eligibility heuristics."""
        if self.policy.max_coverage_amount <= 0:
            return 0.0
        return self.claim.claim_amount / self.policy.max_coverage_amount
