"""
app/components/fraud_gauge.py

Renders the fraud risk score as an SVG arc gauge -- an at-a-glance visual
for the "Fraud Analysis" section, colored by risk tier.
"""

from __future__ import annotations

import streamlit as st

_COLORS = {"LOW": "#3FB68B", "MEDIUM": "#E8A33D", "HIGH": "#E1584F"}


def render_fraud_gauge(score: float, risk_tier: str) -> None:
    """Render a semicircular gauge for a 0-100 fraud risk score."""
    color = _COLORS.get(risk_tier, "#8C97A8")
    score = max(0.0, min(100.0, score))

    # Semicircle arc: map score 0-100 to angle -90..90 degrees.
    import math

    radius = 80
    cx, cy = 100, 95
    angle_deg = -90 + (score / 100.0) * 180
    angle_rad = math.radians(angle_deg)
    needle_x = cx + radius * 0.82 * math.cos(angle_rad)
    needle_y = cy + radius * 0.82 * math.sin(angle_rad)

    svg = f"""
    <svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:260px;display:block;margin:0 auto;">
        <path d="M 20 95 A 80 80 0 0 1 180 95" fill="none" stroke="#263042" stroke-width="14" stroke-linecap="round"/>
        <path d="M 20 95 A 80 80 0 0 1 180 95" fill="none" stroke="{color}" stroke-width="14"
              stroke-linecap="round"
              stroke-dasharray="{score * 2.51} 999"/>
        <circle cx="{cx}" cy="{cy}" r="5" fill="{color}"/>
        <line x1="{cx}" y1="{cy}" x2="{needle_x:.1f}" y2="{needle_y:.1f}" stroke="{color}" stroke-width="3" stroke-linecap="round"/>
        <text x="100" y="80" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="26" font-weight="600" fill="#E9EDF3">{score:.0f}</text>
        <text x="100" y="98" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="#8C97A8">/ 100</text>
    </svg>
    """
    st.markdown(svg, unsafe_allow_html=True)
    st.markdown(
        f'<p class="gauge-label">Risk tier: <b style="color:{color}">{risk_tier}</b></p>',
        unsafe_allow_html=True,
    )
