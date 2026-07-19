"""
schemas/enums.py

Centralized enumerations used across the entire application.

Keeping enums in a single module prevents "magic string" drift between the
LangGraph workflow, the agents, the decision engine, and the Streamlit UI.
Any new status/category value MUST be added here first.
"""

from enum import Enum


class ClaimStatus(str, Enum):
    """Final (or in-progress) status of an insurance claim."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"


class FraudRisk(str, Enum):
    """Fraud risk tier produced by the Fraud Detection Agent."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DocumentType(str, Enum):
    """Supported claim-supporting document categories."""

    POLICY_DOCUMENT = "POLICY_DOCUMENT"
    IDENTITY_PROOF = "IDENTITY_PROOF"
    MEDICAL_REPORT = "MEDICAL_REPORT"
    POLICE_REPORT = "POLICE_REPORT"
    INVOICE_RECEIPT = "INVOICE_RECEIPT"
    INCIDENT_PHOTO = "INCIDENT_PHOTO"
    OTHER = "OTHER"


class ClaimType(str, Enum):
    """Type of insurance claim being filed."""

    HEALTH = "HEALTH"
    MOTOR = "MOTOR"
    LIFE = "LIFE"
    PROPERTY = "PROPERTY"
    TRAVEL = "TRAVEL"


class PolicyStatus(str, Enum):
    """Underlying policy state, independent of the claim itself."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    LAPSED = "LAPSED"
    CANCELLED = "CANCELLED"


class WorkflowNode(str, Enum):
    """Node identifiers used by the LangGraph graph and execution logger.

    Using an enum (instead of raw strings) for node names avoids typos when
    wiring conditional edges in ``langgraph_workflow/graph_builder.py``.
    """

    EXTRACT_CLAIM_INFO = "extract_claim_info"
    DOCUMENT_VERIFICATION = "document_verification"
    ELIGIBILITY_CHECK = "eligibility_check"
    FRAUD_DETECTION = "fraud_detection"
    MERGE_RESULTS = "merge_results"
    CLAIM_SUMMARY = "claim_summary"
    DECISION_ENGINE = "decision_engine"
    HUMAN_APPROVAL = "human_approval"
    APPROVE = "approve"
    REJECT = "reject"


class LogLevel(str, Enum):
    """Severity levels for structured execution log entries."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
