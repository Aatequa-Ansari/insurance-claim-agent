"""
langgraph_workflow/edges.py

Conditional routing logic for the claim-processing StateGraph.

Only one routing decision point exists in this workflow: after the
Decision Engine node runs, the graph either terminates (APPROVED /
REJECTED) or continues to the Human Approval node (HUMAN_REVIEW). Keeping
this as a pure function of state (rather than embedding routing logic in
the node itself) is what makes the graph's control flow independently
testable and visible in the Mermaid diagram.
"""

from __future__ import annotations

from langgraph.graph import END

from core.utils.logger import get_logger
from schemas.enums import ClaimStatus, WorkflowNode
from schemas.state import ClaimState

logger = get_logger(__name__)


def route_after_decision(state: ClaimState) -> str:
    """Route to the Human Approval node, or terminate, based on the decision status."""
    decision = state.get("decision")
    if decision is None:
        logger.error("route_after_decision called with no decision in state; defaulting to END")
        return END

    if decision.status == ClaimStatus.HUMAN_REVIEW:
        return WorkflowNode.HUMAN_APPROVAL.value

    return END
