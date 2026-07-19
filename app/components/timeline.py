"""
app/components/timeline.py

Renders the workflow's ``execution_log`` as a vertical timeline -- used by
the "Agent Logs" / "Workflow Timeline" section so reviewers can see
exactly which node ran, when, with what result, and how long it took.
"""

from __future__ import annotations

import streamlit as st

_LEVEL_COLOR = {
    "INFO": "#8C97A8",
    "SUCCESS": "#3FB68B",
    "WARNING": "#E8A33D",
    "ERROR": "#E1584F",
}


def render_timeline(execution_log: list[dict]) -> None:
    """Render a list of ``ExecutionLogEntry`` dicts as a styled timeline."""
    if not execution_log:
        st.caption("No execution log entries yet.")
        return

    items_html = []
    for entry in execution_log:
        color = _LEVEL_COLOR.get(entry.get("level", "INFO"), "#8C97A8")
        duration = entry.get("duration_ms")
        duration_str = f" &middot; {duration:.0f}ms" if duration else ""
        items_html.append(
            f"""
            <div class="timeline-item">
                <div class="timeline-node" style="color:{color};">{entry.get('node', '')}</div>
                <div class="timeline-msg">{entry.get('message', '')}</div>
                <div class="timeline-time">{entry.get('timestamp', '')}{duration_str}</div>
            </div>
            """
        )

    st.markdown(f'<div class="timeline">{"".join(items_html)}</div>', unsafe_allow_html=True)
