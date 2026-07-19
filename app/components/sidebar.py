"""
app/components/sidebar.py

Renders the branded sidebar shown on every page: the "brand seal" header
plus a snapshot of the current claim (if any) in progress.
"""

from __future__ import annotations

import streamlit as st

from core.config.settings import get_settings


def render_sidebar_brand() -> None:
    """Render the seal + title block at the top of the sidebar."""
    with st.sidebar:
        st.markdown(
            """
            <div class="brand-header">
                <div class="brand-seal">AI</div>
                <div>
                    <p class="brand-title">Meridian Claims</p>
                    <p class="brand-subtitle">AI Insurance Claim Processing Agent</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        settings = get_settings()
        if not settings.is_configured:
            st.warning(
                "GOOGLE_API_KEY not set -- agents will run in deterministic "
                "fallback mode (rule-based results, templated summaries).",
                icon="⚠️",
            )

        claim_history = st.session_state.get("claim_history", [])
        st.markdown("---")
        st.caption(f"Claims processed this session: **{len(claim_history)}**")
