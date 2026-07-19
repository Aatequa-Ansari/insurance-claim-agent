"""
schemas/state.py

Defines ``ClaimState`` -- the single typed object threaded through every
node of the LangGraph workflow -- plus supporting types for execution
logging and retry bookkeeping.

Design notes
------------
LangGraph's ``StateGraph`` works most predictably with a ``TypedDict`` (it
uses it to compute reducers / merge behavior for parallel branches), so the
graph-facing state is a TypedDict rather than a Pydantic BaseModel. Pydantic
models (``ClaimInput``, ``VerificationResult``, etc.) are nested *inside*
it for validation, and are converted at the boundaries (service layer) --
see ``core/services/claim_service.py``.

Parallel-branch safety: ``document_verification``, ``eligibility_check``
and ``fraud_detection`` each write to a *different* key
(``verification_result`` / ``eligibility_result`` / ``fraud_result``), so
there is no write conflict when LangGraph fans them out concurrently. The
``execution_log`` key uses an ``operator.add`` reducer so log entries from
parallel branches are appended rather than overwritten.
"""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, Optional, TypedDict

from schemas.claim import ClaimInput
from schemas.enums import LogLevel, WorkflowNode
from schemas.results import (
    ClaimSummary,
    Decision,
    EligibilityResult,
    FraudResult,
    HumanReviewOutcome,
    VerificationResult,
)


class ExecutionLogEntry(TypedDict):
    """A single structured log line surfaced in the Streamlit 'Agent Logs' panel."""

    timestamp: str
    node: str
    level: str
    message: str
    duration_ms: Optional[float]


def make_log_entry(
    node: WorkflowNode | str,
    message: str,
    level: LogLevel = LogLevel.INFO,
    duration_ms: Optional[float] = None,
) -> ExecutionLogEntry:
    """Factory for a well-formed :class:`ExecutionLogEntry`.

    Centralizing construction avoids inconsistent timestamp formatting
    across the five agents and the graph nodes.
    """
    node_value = node.value if isinstance(node, WorkflowNode) else str(node)
    return ExecutionLogEntry(
        timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        node=node_value,
        level=level.value,
        message=message,
        duration_ms=duration_ms,
    )


class ClaimState(TypedDict, total=False):
    """Shared LangGraph state for one claim's end-to-end processing.

    ``total=False`` because most keys are only populated as the claim
    progresses through the graph; nodes must defensively check for
    ``None`` / missing keys before reading upstream results.
    """

    # --- Input ---
    claim_input: ClaimInput

    # --- Parallel agent outputs (each written by exactly one node) ---
    verification_result: Optional[VerificationResult]
    eligibility_result: Optional[EligibilityResult]
    fraud_result: Optional[FraudResult]

    # --- Downstream sequential outputs ---
    claim_summary: Optional[ClaimSummary]
    decision: Optional[Decision]

    # --- Human-in-the-loop ---
    requires_human_review: bool
    human_review_outcome: Optional[HumanReviewOutcome]
    is_paused_for_review: bool

    # --- Observability / resilience ---
    execution_log: Annotated[list[ExecutionLogEntry], operator.add]
    retry_count: dict[str, int]
    errors: Annotated[list[str], operator.add]

    # --- Workflow bookkeeping ---
    current_node: Optional[str]
    is_complete: bool


def new_claim_state(claim_input: ClaimInput) -> ClaimState:
    """Build a freshly-initialized :class:`ClaimState` for a new claim run."""
    return ClaimState(
        claim_input=claim_input,
        verification_result=None,
        eligibility_result=None,
        fraud_result=None,
        claim_summary=None,
        decision=None,
        requires_human_review=False,
        human_review_outcome=None,
        is_paused_for_review=False,
        execution_log=[
            make_log_entry(
                WorkflowNode.EXTRACT_CLAIM_INFO,
                f"Initialized workflow for claim {claim_input.claim_id}",
                LogLevel.INFO,
            )
        ],
        retry_count={},
        errors=[],
        current_node=None,
        is_complete=False,
    )
