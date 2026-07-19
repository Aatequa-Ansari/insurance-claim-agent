"""
app/components/decision_card.py

Renders the final decision as an official-looking "stamp" -- the visual
signature element of the dashboard -- plus the reasoning text beneath it.
"""

from __future__ import annotations

import streamlit as st

from schemas.enums import ClaimStatus
from schemas.results import Decision

_STAMP_STYLE = {
    ClaimStatus.APPROVED: ("stamp-approved", "APPROVED"),
    ClaimStatus.HUMAN_APPROVED: ("stamp-approved", "APPROVED"),
    ClaimStatus.REJECTED: ("stamp-rejected", "REJECTED"),
    ClaimStatus.HUMAN_REJECTED: ("stamp-rejected", "REJECTED"),
    ClaimStatus.HUMAN_REVIEW: ("stamp-review", "UNDER REVIEW"),
}


def render_decision_stamp(decision: Decision) -> None:
    """Render the decision as a rotated stamp with its reasoning below."""
    css_class, label = _STAMP_STYLE.get(decision.status, ("stamp-review", decision.status.value))

    st.markdown(
        f"""
        <div class="stamp-wrap">
            <div class="stamp {css_class}">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="text-align:center;color:#8C97A8;max-width:520px;margin:8px auto 0 auto;">{decision.reason}</p>',
        unsafe_allow_html=True,
    )
    if decision.decided_by != "SYSTEM":
        st.markdown(
            f'<p style="text-align:center;color:#8C97A8;font-size:0.78rem;">Decided by {decision.decided_by}</p>',
            unsafe_allow_html=True,
        )
