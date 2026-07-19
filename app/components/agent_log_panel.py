"""
app/components/agent_log_panel.py

Renders the three parallel agent outputs (Document Verification,
Eligibility, Fraud Detection) as expandable evidence cards, plus the
Claim Summary agent's executive write-up. Used on both the live results
view and the paused human-review view.
"""

from __future__ import annotations

import streamlit as st

from app.components.fraud_gauge import render_fraud_gauge
from app.components.status_chip import risk_chip_html
from schemas.results import ClaimSummary, EligibilityResult, FraudResult, VerificationResult


def render_verification_card(result: VerificationResult) -> None:
    with st.expander(
        f"📋 Document Verification -- {'Complete' if result.is_complete else 'Incomplete'} "
        f"({result.completeness_score:.0f}%)",
        expanded=not result.is_complete,
    ):
        st.progress(min(result.completeness_score / 100, 1.0))
        if result.missing_documents:
            st.markdown(
                "**Missing:** " + ", ".join(d.value.replace("_", " ") for d in result.missing_documents)
            )
        for check in result.document_checks:
            icon = "✅" if check.is_present and check.is_valid else "❌"
            st.markdown(f"{icon} **{check.document_type.value.replace('_', ' ')}** -- {check.notes}")
        st.caption(result.summary)


def render_eligibility_card(result: EligibilityResult) -> None:
    with st.expander(
        f"🛡️ Eligibility Check -- {'Eligible' if result.is_eligible else 'Not Eligible'}",
        expanded=not result.is_eligible,
    ):
        checks = {
            "Policy Active": result.policy_active,
            "Within Coverage Period": result.within_coverage_period,
            "Waiting Period Satisfied": result.waiting_period_satisfied,
            "Claim Type Covered": result.claim_type_covered,
            "Within Max Coverage": result.within_max_coverage,
        }
        cols = st.columns(len(checks))
        for col, (label, passed) in zip(cols, checks.items()):
            with col:
                st.markdown(f"{'✅' if passed else '❌'}<br><small>{label}</small>", unsafe_allow_html=True)
        if result.ineligibility_reasons:
            st.markdown("**Reasons:**")
            for r in result.ineligibility_reasons:
                st.markdown(f"- {r}")
        st.caption(result.summary)


def render_fraud_card(result: FraudResult) -> None:
    with st.expander(f"🔍 Fraud Analysis -- {result.fraud_risk.value} Risk", expanded=result.fraud_risk.value != "LOW"):
        col1, col2 = st.columns([1, 2])
        with col1:
            render_fraud_gauge(result.risk_score, result.fraud_risk.value)
        with col2:
            st.markdown(risk_chip_html(result.fraud_risk.value), unsafe_allow_html=True)
            if result.is_duplicate_suspected:
                st.markdown("⚠️ **Duplicate/frequent claimant pattern suspected**")
            if result.suspicious_patterns:
                st.markdown("**Suspicious patterns:** " + ", ".join(result.suspicious_patterns))
            if result.reasons:
                st.markdown("**Reasons:**")
                for r in result.reasons:
                    st.markdown(f"- {r}")
            st.caption(result.summary)


def render_summary_card(summary: ClaimSummary) -> None:
    st.markdown('<div class="card"><div class="card-title">Executive Claim Summary</div>', unsafe_allow_html=True)
    st.markdown(summary.executive_summary)
    st.markdown("**Evidence Summary**")
    st.markdown(summary.evidence_summary)
    st.markdown("**Business Justification**")
    st.markdown(summary.business_justification)
    if summary.supporting_information:
        st.markdown("**Supporting Information**")
        for item in summary.supporting_information:
            st.markdown(f"- {item}")
    st.markdown("</div>", unsafe_allow_html=True)
