"""
app/pages/claim_history.py

Lists every claim processed so far in this browser session, with status
chips, so a reviewer can see a running log of decisions.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.sidebar import render_sidebar_brand
from app.components.status_chip import status_chip_html
from schemas.enums import ClaimStatus


def _load_css() -> None:
    css_path = Path(__file__).resolve().parents[1] / "styles" / "theme.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def main() -> None:
    _load_css()
    render_sidebar_brand()

    st.markdown('<p class="brand-title">Claim History</p>', unsafe_allow_html=True)
    st.caption("All claims processed in this session (session-scoped; not persisted across restarts).")

    history = st.session_state.get("claim_history", [])
    if not history:
        st.info("No claims processed yet this session. Head to **New Claim** to get started.")
        return

    for record in reversed(history):
        try:
            status_enum = ClaimStatus(record["status"])
            chip = status_chip_html(status_enum)
        except ValueError:
            chip = f'<span class="chip chip-pending">{record["status"]}</span>'

        st.markdown(
            f"""
            <div class="card" style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span class="ledger" style="font-weight:600;">{record['claim_id']}</span>
                    &nbsp;&nbsp;<span style="color:#8C97A8;">{record['holder']}</span>
                </div>
                <div style="display:flex;align-items:center;gap:14px;">
                    <span class="ledger">₹ {record['amount']:,.2f}</span>
                    {chip}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
