"""
langgraph_workflow/nodes.py

Node functions for the claim-processing StateGraph. Each node is a plain
function ``(state: ClaimState) -> dict`` that LangGraph merges back into
the shared state (per the reducers defined in ``schemas/state.py``).

Nodes are intentionally thin: they extract what they need from state,
delegate to the relevant agent, time the call, append an execution-log
entry, and return only the keys they own. This keeps the graph wiring
(``graph_builder.py``) simple and keeps agent logic independently
unit-testable.
"""

from __future__ import annotations

import time

from langgraph.types import interrupt

from agents.claim_summary_agent import ClaimSummaryAgent
from agents.document_verification_agent import DocumentVerificationAgent
from agents.eligibility_agent import EligibilityAgent
from agents.fraud_detection_agent import FraudDetectionAgent
from agents.human_approval_agent import HumanApprovalAgent
from core.utils.logger import get_logger
from schemas.enums import ClaimStatus, LogLevel, WorkflowNode
from schemas.results import Decision, HumanReviewOutcome
from schemas.state import ClaimState, make_log_entry

logger = get_logger(__name__)

# Agents are stateless-enough to share single instances across node calls.
_doc_agent = DocumentVerificationAgent()
_eligibility_agent = EligibilityAgent()
_fraud_agent = FraudDetectionAgent()
_summary_agent = ClaimSummaryAgent()
_human_agent = HumanApprovalAgent()


def _log(node: WorkflowNode, message: str, level: LogLevel = LogLevel.INFO, duration_ms: float | None = None) -> list:
    return [make_log_entry(node, message, level, duration_ms)]


def extract_claim_info_node(state: ClaimState) -> dict:
    """Entry node: validates the claim is present and kicks off the workflow.

    The actual parsing of form input into ``ClaimInput`` happens in
    ``core/services/claim_service.py`` before the graph is invoked -- this
    node's job is purely to confirm the seed state and emit the first
    workflow-level log line.
    """
    claim_input = state["claim_input"]
    logger.info("Extracting claim info for %s", claim_input.claim_id)
    return {
        "current_node": WorkflowNode.EXTRACT_CLAIM_INFO.value,
        "execution_log": _log(
            WorkflowNode.EXTRACT_CLAIM_INFO,
            f"Claim {claim_input.claim_id} accepted for processing "
            f"({len(claim_input.documents)} document(s), claim type "
            f"{claim_input.incident.claim_type.value}).",
        ),
    }


def document_verification_node(state: ClaimState) -> dict:
    start = time.perf_counter()
    result = _doc_agent.evaluate(state["claim_input"])
    duration_ms = (time.perf_counter() - start) * 1000
    level = LogLevel.SUCCESS if result.is_complete else LogLevel.WARNING
    return {
        "verification_result": result,
        "execution_log": _log(
            WorkflowNode.DOCUMENT_VERIFICATION,
            f"Completeness {result.completeness_score:.0f}% -- "
            f"{'all documents present' if result.is_complete else f'{len(result.missing_documents)} missing'}.",
            level,
            duration_ms,
        ),
    }


def eligibility_check_node(state: ClaimState) -> dict:
    start = time.perf_counter()
    result = _eligibility_agent.evaluate(state["claim_input"])
    duration_ms = (time.perf_counter() - start) * 1000
    level = LogLevel.SUCCESS if result.is_eligible else LogLevel.WARNING
    return {
        "eligibility_result": result,
        "execution_log": _log(
            WorkflowNode.ELIGIBILITY_CHECK,
            "Claim is eligible." if result.is_eligible else f"Claim is NOT eligible: {'; '.join(result.ineligibility_reasons)}",
            level,
            duration_ms,
        ),
    }


def fraud_detection_node(state: ClaimState) -> dict:
    start = time.perf_counter()
    result = _fraud_agent.evaluate(state["claim_input"])
    duration_ms = (time.perf_counter() - start) * 1000
    level = {
        "LOW": LogLevel.SUCCESS,
        "MEDIUM": LogLevel.WARNING,
        "HIGH": LogLevel.ERROR,
    }[result.fraud_risk.value]
    return {
        "fraud_result": result,
        "execution_log": _log(
            WorkflowNode.FRAUD_DETECTION,
            f"Fraud risk: {result.fraud_risk.value} (score {result.risk_score:.0f}/100).",
            level,
            duration_ms,
        ),
    }


def merge_results_node(state: ClaimState) -> dict:
    """Synchronization barrier after the parallel fan-out.

    Validates that all three parallel branches completed before the
    workflow proceeds -- LangGraph waits for all incoming edges by default,
    but this explicit check gives a clear error message + log entry if a
    branch somehow produced no result (state validation requirement).
    """
    missing = [
        name
        for name, value in (
            ("verification_result", state.get("verification_result")),
            ("eligibility_result", state.get("eligibility_result")),
            ("fraud_result", state.get("fraud_result")),
        )
        if value is None
    ]
    if missing:
        message = f"Merge failed -- missing results from: {', '.join(missing)}"
        logger.error(message)
        return {
            "errors": [message],
            "execution_log": _log(WorkflowNode.MERGE_RESULTS, message, LogLevel.ERROR),
        }
    return {
        "execution_log": _log(
            WorkflowNode.MERGE_RESULTS,
            "All parallel checks (document verification, eligibility, fraud detection) completed.",
        )
    }


def claim_summary_node(state: ClaimState) -> dict:
    start = time.perf_counter()
    summary = _summary_agent.evaluate(
        state["claim_input"],
        state["verification_result"],
        state["eligibility_result"],
        state["fraud_result"],
    )
    duration_ms = (time.perf_counter() - start) * 1000
    return {
        "claim_summary": summary,
        "execution_log": _log(
            WorkflowNode.CLAIM_SUMMARY, "Executive claim summary generated.", LogLevel.INFO, duration_ms
        ),
    }


def decision_engine_node(state: ClaimState) -> dict:
    """Applies the deterministic decision rules and records the outcome.

    The actual routing (which downstream node to go to next) is handled by
    the conditional edge function in ``edges.py``; this node's job is only
    to compute and persist the :class:`Decision` object itself so it's
    available for every downstream branch (approve/reject/human_approval).
    """
    claim_input = state["claim_input"]
    verification = state["verification_result"]
    eligibility = state["eligibility_result"]
    fraud = state["fraud_result"]

    if not verification.is_complete:
        decision = Decision(
            status=ClaimStatus.REJECTED,
            reason=f"Required documents missing: {', '.join(d.value for d in verification.missing_documents)}.",
        )
    elif not eligibility.is_eligible:
        decision = Decision(
            status=ClaimStatus.REJECTED,
            reason="Claim is not eligible: " + "; ".join(eligibility.ineligibility_reasons),
        )
    else:
        should_escalate, escalation_reason = _human_agent.requires_escalation(
            claim_input, verification, eligibility, fraud
        )
        if should_escalate:
            decision = Decision(
                status=ClaimStatus.HUMAN_REVIEW,
                reason=escalation_reason,
                requires_human_review=True,
            )
        else:
            decision = Decision(
                status=ClaimStatus.APPROVED,
                reason="All checks passed: documents complete, policy eligible, fraud risk low.",
            )

    return {
        "decision": decision,
        "requires_human_review": decision.status == ClaimStatus.HUMAN_REVIEW,
        "execution_log": _log(
            WorkflowNode.DECISION_ENGINE,
            f"Decision: {decision.status.value} -- {decision.reason}",
            LogLevel.SUCCESS if decision.status == ClaimStatus.APPROVED else LogLevel.WARNING,
        ),
        "is_complete": decision.status != ClaimStatus.HUMAN_REVIEW,
    }


def human_approval_node(state: ClaimState) -> dict:
    """Pauses the graph for a human decision using LangGraph's ``interrupt()``.

    When this node runs, execution halts and the interrupt payload
    (evidence for the reviewer) is surfaced to the caller (see
    ``core/services/claim_service.py``). The Streamlit UI renders it and,
    once the reviewer acts, the service resumes the graph with
    ``Command(resume={...})`` -- at which point ``interrupt()`` returns the
    resume payload and this function continues from that point.
    """
    claim_input = state["claim_input"]
    decision = state["decision"]

    payload = {
        "claim_id": claim_input.claim_id,
        "reason": decision.reason if decision else "Escalated for manual review.",
        "verification_result": state["verification_result"].model_dump(mode="json"),
        "eligibility_result": state["eligibility_result"].model_dump(mode="json"),
        "fraud_result": state["fraud_result"].model_dump(mode="json"),
        "claim_summary": state["claim_summary"].model_dump(mode="json") if state.get("claim_summary") else None,
    }

    resume_payload = interrupt(payload)

    outcome = HumanReviewOutcome.model_validate(resume_payload)
    final_decision = _human_agent.finalize(outcome)

    return {
        "human_review_outcome": outcome,
        "decision": final_decision,
        "is_paused_for_review": False,
        "is_complete": True,
        "execution_log": _log(
            WorkflowNode.HUMAN_APPROVAL,
            f"Human review outcome: {final_decision.status.value} by {outcome.reviewer_name}.",
            LogLevel.SUCCESS if outcome.approved else LogLevel.ERROR,
        ),
    }
