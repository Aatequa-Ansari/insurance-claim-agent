"""
agents/human_approval_agent.py

Agent 5: Human Approval Agent.

Responsibilities (per assignment spec): triggered when fraud risk is high,
claim amount is high, information is missing/conflicting, or manual
review is otherwise required. This agent does not call the LLM -- its job
is to decide (deterministically, from the other agents' outputs) *whether*
escalation is required, and later, once a human reviewer responds, to
translate that decision into a final :class:`Decision`.

The actual "pause and wait for a human" mechanic is implemented at the
LangGraph level via ``interrupt()`` in ``langgraph_workflow/nodes.py`` --
this class holds the pure business logic so it can be unit-tested without
a running graph.
"""

from __future__ import annotations

from core.config.settings import Settings, get_settings
from schemas.claim import ClaimInput
from schemas.enums import ClaimStatus, FraudRisk, WorkflowNode
from schemas.results import (
    Decision,
    EligibilityResult,
    FraudResult,
    HumanReviewOutcome,
    VerificationResult,
)


class HumanApprovalAgent:
    """Determines escalation triggers and finalizes human review outcomes."""

    node = WorkflowNode.HUMAN_APPROVAL

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def requires_escalation(
        self,
        claim_input: ClaimInput,
        verification: VerificationResult,
        eligibility: EligibilityResult,
        fraud: FraudResult,
    ) -> tuple[bool, str]:
        """Return ``(should_escalate, reason)`` given all upstream agent outputs.

        Note: missing-document and ineligibility cases are handled as
        auto-rejections upstream (see ``langgraph_workflow/edges.py``) and
        never reach this method -- this method only evaluates escalation
        triggers for otherwise-eligible, document-complete claims.
        """
        if fraud.fraud_risk == FraudRisk.HIGH:
            return True, f"High fraud risk detected (score {fraud.risk_score:.0f}/100)."

        if fraud.fraud_risk == FraudRisk.MEDIUM:
            return True, f"Medium fraud risk detected (score {fraud.risk_score:.0f}/100); manual review recommended."

        ratio = claim_input.high_value_threshold_fraction()
        if claim_input.claim.claim_amount >= self.settings.high_value_claim_threshold:
            return True, (
                f"Claim amount {claim_input.claim.currency} {claim_input.claim.claim_amount:,.2f} "
                f"meets or exceeds the high-value threshold "
                f"({self.settings.high_value_claim_threshold:,.2f})."
            )
        if ratio >= self.settings.high_value_coverage_fraction:
            return True, f"Claim amount is {ratio:.0%} of maximum policy coverage, exceeding the review threshold."

        return False, ""

    @staticmethod
    def finalize(outcome: HumanReviewOutcome) -> Decision:
        """Convert a human reviewer's decision into a final :class:`Decision`."""
        status = ClaimStatus.HUMAN_APPROVED if outcome.approved else ClaimStatus.HUMAN_REJECTED
        reason = outcome.comments.strip() or (
            "Approved by human reviewer." if outcome.approved else "Rejected by human reviewer."
        )
        return Decision(
            status=status,
            reason=f"[Reviewed by {outcome.reviewer_name}] {reason}",
            requires_human_review=True,
            decided_by=outcome.reviewer_name,
        )
