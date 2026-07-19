"""
core/config/business_rules.py

Declarative business rules for claim adjudication, kept separate from
``settings.py`` (environment/infra config) and separate from the decision
engine's control flow (``langgraph_workflow/edges.py``).

Isolating rules here means a non-engineer (e.g. an actual claims analyst)
could review or tune thresholds without touching workflow code, and it
gives us one place to unit-test rule values against the 5 mandated
scenarios.
"""

from __future__ import annotations

from schemas.enums import DocumentType, ClaimType

# Documents required for every claim, regardless of type.
BASE_REQUIRED_DOCUMENTS: list[DocumentType] = [
    DocumentType.POLICY_DOCUMENT,
    DocumentType.IDENTITY_PROOF,
]

# Additional documents required per claim type.
CLAIM_TYPE_REQUIRED_DOCUMENTS: dict[ClaimType, list[DocumentType]] = {
    ClaimType.HEALTH: [DocumentType.MEDICAL_REPORT, DocumentType.INVOICE_RECEIPT],
    ClaimType.MOTOR: [DocumentType.POLICE_REPORT, DocumentType.INCIDENT_PHOTO, DocumentType.INVOICE_RECEIPT],
    ClaimType.LIFE: [DocumentType.MEDICAL_REPORT],
    ClaimType.PROPERTY: [DocumentType.INCIDENT_PHOTO, DocumentType.INVOICE_RECEIPT],
    ClaimType.TRAVEL: [DocumentType.INVOICE_RECEIPT],
}


def required_documents_for(claim_type: ClaimType) -> list[DocumentType]:
    """Return the full set of required document types for a given claim type."""
    return list(dict.fromkeys(BASE_REQUIRED_DOCUMENTS + CLAIM_TYPE_REQUIRED_DOCUMENTS.get(claim_type, [])))


# Duplicate-claim detection window (used by Fraud Detection Agent heuristics).
DUPLICATE_CLAIM_WINDOW_DAYS = 30

# A policy younger than this is treated as a fraud risk factor (fresh policy + big claim).
MIN_POLICY_AGE_DAYS_LOW_RISK = 30

# Previous-claims-count threshold that nudges fraud risk upward.
FREQUENT_CLAIMANT_THRESHOLD = 3
