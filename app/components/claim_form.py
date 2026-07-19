"""
app/components/claim_form.py

Renders the claim intake form (policy details, incident details, claim
details) and returns the raw field values as a dict when submitted, or
``None`` otherwise. Building ``ClaimInput`` (with Pydantic validation)
from these raw values happens in the calling page, so validation errors
can be displayed inline without losing the user's other entries.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import streamlit as st

from schemas.enums import ClaimType


def render_claim_form(prefill: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """Render the claim intake form.

    Args:
        prefill: optional dict of default values (used by "Load Demo Case").

    Returns:
        A dict of raw form values if the form was submitted this run,
        otherwise ``None``.
    """
    prefill = prefill or {}
    today = date.today()

    with st.form("claim_intake_form", clear_on_submit=False):
        st.markdown('<div class="card-title">Policy Details</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            policy_number = st.text_input("Policy Number", value=prefill.get("policy_number", "POL-100234"))
            policy_holder_name = st.text_input("Policy Holder Name", value=prefill.get("policy_holder_name", ""))
            max_coverage_amount = st.number_input(
                "Maximum Coverage Amount (INR)",
                min_value=1.0,
                value=float(prefill.get("max_coverage_amount", 1_000_000.0)),
                step=10000.0,
            )
        with col2:
            policy_start_date = st.date_input(
                "Policy Start Date", value=prefill.get("policy_start_date", today - timedelta(days=730))
            )
            policy_end_date = st.date_input(
                "Policy End Date", value=prefill.get("policy_end_date", today + timedelta(days=365))
            )
            waiting_period_days = st.number_input(
                "Waiting Period (days)", min_value=0, value=int(prefill.get("waiting_period_days", 0))
            )

        st.markdown('<div class="card-title" style="margin-top:14px;">Incident Details</div>', unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            claim_type = st.selectbox(
                "Claim Type",
                options=[c.value for c in ClaimType],
                index=[c.value for c in ClaimType].index(prefill.get("claim_type", ClaimType.MOTOR.value)),
            )
            incident_date = st.date_input("Incident Date", value=prefill.get("incident_date", today - timedelta(days=10)))
        with col4:
            incident_location = st.text_input("Incident Location", value=prefill.get("incident_location", ""))

        incident_description = st.text_area(
            "Incident Description",
            value=prefill.get("incident_description", ""),
            height=90,
            placeholder="Describe what happened, when, and how the loss/injury occurred...",
        )

        st.markdown('<div class="card-title" style="margin-top:14px;">Claim Details</div>', unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            claim_amount = st.number_input(
                "Claim Amount (INR)", min_value=1.0, value=float(prefill.get("claim_amount", 50000.0)), step=1000.0
            )
        with col6:
            previous_claims_count = st.number_input(
                "Previous Claims on This Policy", min_value=0, value=int(prefill.get("previous_claims_count", 0))
            )

        submitted = st.form_submit_button("Run Claim Workflow →", use_container_width=True)

    if not submitted:
        return None

    return {
        "policy_number": policy_number,
        "policy_holder_name": policy_holder_name,
        "max_coverage_amount": max_coverage_amount,
        "policy_start_date": policy_start_date,
        "policy_end_date": policy_end_date,
        "waiting_period_days": waiting_period_days,
        "claim_type": claim_type,
        "incident_date": incident_date,
        "incident_location": incident_location,
        "incident_description": incident_description,
        "claim_amount": claim_amount,
        "previous_claims_count": previous_claims_count,
    }
