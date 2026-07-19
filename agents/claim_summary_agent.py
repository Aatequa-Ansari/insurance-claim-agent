"""
agents/claim_summary_agent.py

Agent 4: Claim Summary Agent.

Responsibilities (per assignment spec): generate an executive summary,
evidence summary, business justification, and supporting information,
synthesizing the outputs of the Document Verification, Eligibility, and
Fraud Detection agents.

This is the one agent that is fully LLM-driven (no numeric determinations
to make deterministic) -- but it still degrades gracefully to a templated
summary if the LLM is unavailable, so the workflow never dead-ends.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from prompts.summary_prompt import SYSTEM_PROMPT, build_user_prompt
from schemas.claim import ClaimInput
from schemas.enums import WorkflowNode
from schemas.results import ClaimSummary, EligibilityResult, FraudResult, VerificationResult


class ClaimSummaryAgent(BaseAgent):
    """Synthesizes verification, eligibility, and fraud findings into a case summary."""

    node = WorkflowNode.CLAIM_SUMMARY

    def evaluate(
        self,
        claim_input: ClaimInput,
        verification: VerificationResult,
        eligibility: EligibilityResult,
        fraud: FraudResult,
    ) -> ClaimSummary:
        context = {
            "claim_id": claim_input.claim_id,
            "policy_holder_name": claim_input.policy.policy_holder_name,
            "claim_type": claim_input.incident.claim_type.value,
            "claim_amount": claim_input.claim.claim_amount,
            "currency": claim_input.claim.currency,
            "incident_description": claim_input.incident.incident_description,
            "document_verification": {
                "is_complete": verification.is_complete,
                "completeness_score": verification.completeness_score,
                "missing_documents": [d.value for d in verification.missing_documents],
                "summary": verification.summary,
            },
            "eligibility": {
                "is_eligible": eligibility.is_eligible,
                "ineligibility_reasons": eligibility.ineligibility_reasons,
                "summary": eligibility.summary,
            },
            "fraud": {
                "fraud_risk": fraud.fraud_risk.value,
                "risk_score": fraud.risk_score,
                "reasons": fraud.reasons,
                "summary": fraud.summary,
            },
        }

        fallback = {
            "executive_summary": (
                f"Claim {claim_input.claim_id} for {claim_input.claim.currency} "
                f"{claim_input.claim.claim_amount:,.2f} was reviewed across document "
                f"verification, eligibility, and fraud analysis."
            ),
            "evidence_summary": verification.summary,
            "business_justification": (
                eligibility.summary + " " + fraud.summary
            ).strip(),
            "supporting_information": [
                f"Document completeness: {verification.completeness_score:.0f}%",
                f"Eligibility: {'PASS' if eligibility.is_eligible else 'FAIL'}",
                f"Fraud risk: {fraud.fraud_risk.value} ({fraud.risk_score:.0f}/100)",
            ],
        }

        return self._safe_llm_narrative(
            SYSTEM_PROMPT,
            build_user_prompt(context),
            ClaimSummary,
            fallback=fallback,
        )
