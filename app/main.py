"""
app/main.py

Entry point for the Enterprise AI Insurance Claim Processing Agent
Streamlit application. Run with:

    streamlit run app/main.py

This module owns the app-wide ``st.set_page_config`` call (must happen
exactly once, before navigation is built) and defines the sidebar
navigation via ``st.navigation``. Page icons are passed as plain string
literals in Python source (UTF-8 encoded, version-controlled as text) --
deliberately *not* embedded in filenames, since emoji-in-filename can be
mis-decoded by some tools when a zip/archive is extracted on Windows,
producing garbled sidebar labels. This module also renders the "Home"
landing view itself: a brief product overview and session-wide metrics.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable (this file lives at app/main.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.components.sidebar import render_sidebar_brand
from core.config.settings import get_settings

st.set_page_config(
    page_title="Meridian Claims -- AI Claim Processing",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _load_css() -> None:
    css_path = Path(__file__).parent / "styles" / "theme.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def _init_session_state() -> None:
    st.session_state.setdefault("claim_history", [])
    st.session_state.setdefault("active_claim_id", None)


def render_home() -> None:
    """Render the Home / landing page content."""
    _load_css()
    _init_session_state()
    render_sidebar_brand()

    settings = get_settings()

    st.markdown(
        """
        <div class="brand-header" style="border-bottom:none;">
            <div class="brand-seal" style="width:56px;height:56px;font-size:22px;">AI</div>
            <div>
                <p class="brand-title" style="font-size:1.9rem;">Meridian Claims</p>
                <p class="brand-subtitle">Enterprise AI Insurance Claim Processing Agent -- powered by LangGraph &amp; Gemini 2.5 Flash</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    history = st.session_state.get("claim_history", [])
    approved = sum(1 for c in history if c.get("status", "").startswith("APPROV"))
    rejected = sum(1 for c in history if c.get("status", "").startswith("REJECT"))
    review = sum(1 for c in history if "REVIEW" in c.get("status", ""))

    col1, col2, col3, col4 = st.columns(4)
    tiles = [
        ("Claims Processed", len(history)),
        ("Approved", approved),
        ("Rejected", rejected),
        ("Under / Pending Review", review),
    ]
    for col, (label, value) in zip((col1, col2, col3, col4), tiles):
        with col:
            st.markdown(
                f"""<div class="metric-tile"><div class="metric-value">{value}</div>
                     <div class="metric-label">{label}</div></div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)

    left, right = st.columns([2, 1])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">How this works</div>', unsafe_allow_html=True)
        st.markdown(
            """
This agent automates end-to-end insurance claim adjudication using a **LangGraph**
multi-agent workflow with **Google Gemini 2.5 Flash**:

1. **Extract** claim details from the intake form and uploaded PDFs
2. **Parallel review** -- Document Verification, Eligibility Check, and Fraud
   Detection agents run concurrently
3. **Synthesize** -- a Claim Summary agent produces an executive case file
4. **Decide** -- a deterministic, auditable decision engine approves, rejects,
   or escalates the claim
5. **Human-in-the-loop** -- escalated claims pause for a reviewer's decision,
   right inside this dashboard

Head to **New Claim** in the sidebar to process a claim, or **Load Demo Case**
there to try one of the five built-in test scenarios instantly.
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">System Status</div>', unsafe_allow_html=True)
        st.markdown(f"**Model:** `{settings.gemini_model}`")
        st.markdown(
            f"**Gemini API:** {'🟢 Configured' if settings.is_configured else '🟡 Not configured (fallback mode)'}"
        )
        st.markdown(f"**Environment:** `{settings.environment}`")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.caption(
        "Meridian Claims is a demonstration project. It is not a real insurance "
        "carrier and does not process real policies."
    )


def main() -> None:
    """Build the sidebar navigation and run the selected page."""
    home_page = st.Page(render_home, title="Home", icon="🏠", default=True, url_path="home")
    new_claim_page = st.Page("pages/new_claim.py", title="New Claim", icon="📄", url_path="new-claim")
    dashboard_page = st.Page("pages/dashboard.py", title="Dashboard", icon="📊", url_path="dashboard")
    history_page = st.Page("pages/claim_history.py", title="Claim History", icon="🗂️", url_path="claim-history")

    navigation = st.navigation([home_page, new_claim_page, dashboard_page, history_page])
    navigation.run()


if __name__ == "__main__":
    main()
