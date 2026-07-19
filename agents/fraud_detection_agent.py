"""
agents/fraud_detection_agent.py

Agent 3: Fraud Detection Agent.

Responsibilities (per assignment spec): analyze claim amount, policy age,
duplicate claims, and suspicious patterns; produce a fraud risk tier
(LOW/MEDIUM/HIGH), a numeric risk score, and explained reasons.

The numeric risk score is computed from deterministic heuristics (so it is
reproducible and explainable to a regulator); the LLM adds narrative-level
pattern detection by reading the free-text incident description, and its
findings can raise (never silently lower) the deterministic score.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core.config.business_rules import (
    FREQUENT_CLAIMANT_THRESHOLD,
    MIN_POLICY_AGE_DAYS_LOW_RISK,
)
from core.config.settings import get_settings
from prompts.fraud_detection_prompt import SYSTEM_PROMPT, build_user_prompt
from schemas.claim import ClaimInput
from schemas.enums import FraudRisk, WorkflowNode
from schemas.results import FraudResult


class _FraudNarrative(BaseModel):
    suspicious_patterns: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    summary: str = ""


class FraudDetectionAgent(BaseAgent):
    """Scores a claim's fraud risk using deterministic heuristics + LLM narrative analysis."""

    node = WorkflowNode.FRAUD_DETECTION

    def evaluate(self, claim_input: ClaimInput) -> FraudResult:
        settings = get_settings()
        policy = claim_input.policy
        claim = claim_input.claim

        score = 0.0
        reasons: list[str] = []

        # Heuristic 1: fresh policy + claim shortly after inception.
        policy_age_days = policy.policy_age_days
        if policy_age_days < MIN_POLICY_AGE_DAYS_LOW_RISK:
            score += 25
            reasons.append(
                f"Policy is only {policy_age_days} day(s) old at time of claim "
                f"(threshold: {MIN_POLICY_AGE_DAYS_LOW_RISK})."
            )

        # Heuristic 2: claim amount close to / at max coverage.
        coverage_ratio = claim_input.high_value_threshold_fraction()
        if coverage_ratio >= 0.9:
            score += 30
            reasons.append(f"Claim amount is {coverage_ratio:.0%} of maximum policy coverage.")
        elif coverage_ratio >= 0.7:
            score += 15
            reasons.append(f"Claim amount is {coverage_ratio:.0%} of maximum policy coverage.")

        # Heuristic 3: frequent claimant.
        is_duplicate_suspected = claim.previous_claims_count >= FREQUENT_CLAIMANT_THRESHOLD
        if is_duplicate_suspected:
            score += 25
            reasons.append(
                f"Policyholder has {claim.previous_claims_count} prior claim(s), at/above the "
                f"frequent-claimant threshold ({FREQUENT_CLAIMANT_THRESHOLD})."
            )
        elif claim.previous_claims_count > 0:
            score += 5 * claim.previous_claims_count

        # Heuristic 4: suspiciously round claim amount (common staged-claim pattern).
        if claim.claim_amount % 10000 == 0 and claim.claim_amount >= 50000:
            score += 10
            reasons.append("Claim amount is a suspiciously round figure.")

        score = min(score, 100.0)

        context = {
            "claim_id": claim_input.claim_id,
            "claim_amount": claim.claim_amount,
            "max_coverage_amount": policy.max_coverage_amount,
            "coverage_ratio": round(coverage_ratio, 3),
            "policy_age_days": policy_age_days,
            "previous_claims_count": claim.previous_claims_count,
            "preliminary_risk_score": score,
            "incident_description": claim_input.incident.incident_description,
            "incident_date": str(claim_input.incident.incident_date),
            "claim_type": claim_input.incident.claim_type.value,
        }

        fallback_summary = (
            f"Preliminary rule-based fraud risk score: {score:.0f}/100. "
            + (" ".join(reasons) if reasons else "No significant risk indicators detected.")
        )

        narrative = self._safe_llm_narrative(
            SYSTEM_PROMPT,
            build_user_prompt(context),
            _FraudNarrative,
            fallback={"suspicious_patterns": [], "reasons": [], "summary": fallback_summary},
        )

        # Narrative can add to, never subtract from, the deterministic score --
        # each additional LLM-identified pattern nudges the score up slightly,
        # keeping the auditable numeric floor intact while letting qualitative
        # analysis matter.
        final_score = min(score + 5 * len(narrative.suspicious_patterns), 100.0)
        fraud_risk = self._score_to_tier(final_score, settings.fraud_high_risk_score, settings.fraud_medium_risk_score)

        return FraudResult(
            fraud_risk=fraud_risk,
            risk_score=round(final_score, 2),
            suspicious_patterns=narrative.suspicious_patterns,
            reasons=reasons + narrative.reasons,
            is_duplicate_suspected=is_duplicate_suspected,
            summary=narrative.summary or fallback_summary,
        )

    @staticmethod
    def _score_to_tier(score: float, high_threshold: float, medium_threshold: float) -> FraudRisk:
        if score >= high_threshold:
            return FraudRisk.HIGH
        if score >= medium_threshold:
            return FraudRisk.MEDIUM
        return FraudRisk.LOW
