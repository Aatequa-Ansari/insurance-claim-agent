"""
app/pages/dashboard.py

Aggregate dashboard: session-wide claim metrics, status breakdown chart,
and the LangGraph workflow visualization (Mermaid diagram).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.components.mermaid_diagram import render_mermaid
from app.components.sidebar import render_sidebar_brand
from langgraph_workflow.graph_visualizer import get_mermaid_diagram


def _load_css() -> None:
    css_path = Path(__file__).resolve().parents[1] / "styles" / "theme.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def main() -> None:
    _load_css()
    render_sidebar_brand()

    st.markdown('<p class="brand-title">Claims Dashboard</p>', unsafe_allow_html=True)
    st.caption("Session-wide overview of claims processed by the AI workflow.")

    history = st.session_state.get("claim_history", [])

    if not history:
        st.info("No claims processed yet this session. Head to **New Claim** to get started.")
    else:
        df = pd.DataFrame(history)
        approved = df["status"].str.startswith("APPROV").sum()
        rejected = df["status"].str.startswith("REJECT").sum()
        total_amount = df["amount"].sum()

        c1, c2, c3, c4 = st.columns(4)
        for col, (label, value) in zip(
            (c1, c2, c3, c4),
            [
                ("Total Claims", len(df)),
                ("Approved", int(approved)),
                ("Rejected", int(rejected)),
                ("Total Claim Value (INR)", f"{total_amount:,.0f}"),
            ],
        ):
            with col:
                st.markdown(
                    f'<div class="metric-tile"><div class="metric-value">{value}</div>'
                    f'<div class="metric-label">{label}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title">Status Breakdown</div>', unsafe_allow_html=True)
        status_counts = df["status"].value_counts()
        st.bar_chart(status_counts)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="card"><div class="card-title">Workflow Visualization</div>', unsafe_allow_html=True)
    st.caption("Live topology of the compiled LangGraph claim-processing agent.")
    st.markdown("</div>", unsafe_allow_html=True)

    diagram_source = get_mermaid_diagram()
    render_mermaid(diagram_source)
    with st.expander("View Mermaid source"):
        st.code(diagram_source, language="mermaid")


if __name__ == "__main__":
    main()
