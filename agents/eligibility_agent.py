"""
agents/eligibility_agent.py

Agent 2: Eligibility Check Agent.

Responsibilities (per assignment spec): check policy active status,
policy expiry, coverage, claim type, waiting period, maximum coverage,
and return a structured eligibility result.

All boolean determinations are computed deterministically from policy
dates and amounts -- eligibility is a compliance/contractual matter that
must be reproducible and auditable, not left to LLM judgment. The LLM is
used only to explain the outcome in clear underwriting language.
"""

from __future__ import annotations

from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core.config.business_rules import CLAIM_TYPE_REQUIRED_DOCUMENTS
from prompts.eligibility_prompt import SYSTEM_PROMPT, build_user_prompt
from schemas.claim import ClaimInput
from schemas.enums import PolicyStatus, WorkflowNode
from schemas.results import EligibilityResult


class _EligibilityNarrative(BaseModel):
    summary: str = ""


class EligibilityAgent(BaseAgent):
    """Determines whether a claim is eligible for payout under its policy."""

    node = WorkflowNode.ELIGIBILITY_CHECK

    def evaluate(self, claim_input: ClaimInput) -> EligibilityResult:
        policy = claim_input.policy
        incident = claim_input.incident
        claim = claim_input.claim

        policy_active = policy.policy_status == PolicyStatus.ACTIVE and not policy.is_expired
        within_coverage_period = policy.policy_start_date <= incident.incident_date <= policy.policy_end_date
        days_since_start = (incident.incident_date - policy.policy_start_date).days
        waiting_period_satisfied = days_since_start >= policy.waiting_period_days
        claim_type_covered = incident.claim_type in CLAIM_TYPE_REQUIRED_DOCUMENTS
        within_max_coverage = claim.claim_amount <= policy.max_coverage_amount

        reasons: list[str] = []
        if not policy_active:
            reasons.append("Policy is not active or has expired.")
        if not within_coverage_period:
            reasons.append("Incident date falls outside the policy coverage period.")
        if not waiting_period_satisfied:
            remaining = policy.waiting_period_days - days_since_start
            reasons.append(f"Waiting period not satisfied ({remaining} day(s) remaining).")
        if not claim_type_covered:
            reasons.append(f"Claim type '{incident.claim_type.value}' is not a covered category.")
        if not within_max_coverage:
            reasons.append(
                f"Claim amount ({claim.currency} {claim.claim_amount:,.2f}) exceeds the "
                f"maximum coverage ({claim.currency} {policy.max_coverage_amount:,.2f})."
            )

        is_eligible = len(reasons) == 0

        fallback_summary = (
            "The claim satisfies all eligibility requirements."
            if is_eligible
            else "The claim is not eligible: " + " ".join(reasons)
        )

        context = {
            "claim_id": claim_input.claim_id,
            "policy_active": policy_active,
            "policy_status": policy.policy_status.value,
            "policy_start_date": str(policy.policy_start_date),
            "policy_end_date": str(policy.policy_end_date),
            "incident_date": str(incident.incident_date),
            "within_coverage_period": within_coverage_period,
            "waiting_period_days_required": policy.waiting_period_days,
            "days_since_policy_start": days_since_start,
            "waiting_period_satisfied": waiting_period_satisfied,
            "claim_type": incident.claim_type.value,
            "claim_type_covered": claim_type_covered,
            "claim_amount": claim.claim_amount,
            "max_coverage_amount": policy.max_coverage_amount,
            "within_max_coverage": within_max_coverage,
            "ineligibility_reasons": reasons,
        }

        narrative = self._safe_llm_narrative(
            SYSTEM_PROMPT,
            build_user_prompt(context),
            _EligibilityNarrative,
            fallback={"summary": fallback_summary},
        )

        return EligibilityResult(
            is_eligible=is_eligible,
            policy_active=policy_active,
            within_coverage_period=within_coverage_period,
            waiting_period_satisfied=waiting_period_satisfied,
            claim_type_covered=claim_type_covered,
            within_max_coverage=within_max_coverage,
            ineligibility_reasons=reasons,
            summary=narrative.summary or fallback_summary,
        )
