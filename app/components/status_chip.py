"""
app/components/status_chip.py

Small colored "chip" badges used throughout the UI to show claim status,
fraud risk, and pass/fail states at a glance.
"""

from __future__ import annotations

from schemas.enums import ClaimStatus

_STATUS_CHIP_CLASS = {
    ClaimStatus.APPROVED: "chip-approved",
    ClaimStatus.HUMAN_APPROVED: "chip-approved",
    ClaimStatus.REJECTED: "chip-rejected",
    ClaimStatus.HUMAN_REJECTED: "chip-rejected",
    ClaimStatus.HUMAN_REVIEW: "chip-review",
    ClaimStatus.PENDING: "chip-pending",
    ClaimStatus.IN_PROGRESS: "chip-pending",
}

_STATUS_ICON = {
    ClaimStatus.APPROVED: "✓",
    ClaimStatus.HUMAN_APPROVED: "✓",
    ClaimStatus.REJECTED: "✕",
    ClaimStatus.HUMAN_REJECTED: "✕",
    ClaimStatus.HUMAN_REVIEW: "⏳",
    ClaimStatus.PENDING: "•",
    ClaimStatus.IN_PROGRESS: "•",
}


def status_chip_html(status: ClaimStatus, label: str | None = None) -> str:
    """Return HTML for a single status chip (embed with ``unsafe_allow_html=True``)."""
    css_class = _STATUS_CHIP_CLASS.get(status, "chip-pending")
    icon = _STATUS_ICON.get(status, "•")
    text = label or status.value.replace("_", " ")
    return f'<span class="chip {css_class}">{icon} {text}</span>'


def risk_chip_html(risk_value: str) -> str:
    """Return HTML for a fraud-risk chip (LOW / MEDIUM / HIGH)."""
    mapping = {"LOW": "chip-approved", "MEDIUM": "chip-review", "HIGH": "chip-rejected"}
    css_class = mapping.get(risk_value, "chip-pending")
    return f'<span class="chip {css_class}">{risk_value} RISK</span>'
