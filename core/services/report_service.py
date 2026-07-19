"""
core/services/report_service.py

Generates downloadable claim reports (JSON + PDF) from a completed
``ClaimState``. Used by the Streamlit "Download PDF Report" /
"Download JSON Report" buttons.

PDF generation uses ``fpdf2`` -- pure-Python, no system font/binary
dependencies, so it works unmodified on Streamlit Community Cloud.
``fpdf`` is imported lazily (inside ``build_pdf_report``) rather than at
module level: this file is imported eagerly by the New Claim page, and if
``fpdf2`` were ever missing/broken in a given environment, a top-level
import would crash the *entire page* on load rather than just disabling
the PDF-download feature. JSON report generation has no such dependency
and always works.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.utils.logger import get_logger
from schemas.state import ClaimState

if TYPE_CHECKING:
    from fpdf import FPDF

logger = get_logger(__name__)


class ReportServiceError(RuntimeError):
    """Raised when a report cannot be generated (e.g. a missing optional dependency)."""


class ReportService:
    """Builds JSON and PDF summaries of a finished claim workflow run."""

    def __init__(self, reports_dir: str = "reports") -> None:
        self._reports_dir = Path(reports_dir)
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # JSON report
    # ------------------------------------------------------------------ #
    def build_json_report(self, state: ClaimState) -> str:
        """Serialize the relevant parts of ``state`` into a pretty JSON string."""
        claim_input = state.get("claim_input")
        payload: dict[str, Any] = {
            "claim_id": claim_input.claim_id if claim_input else None,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "claim_input": claim_input.model_dump(mode="json") if claim_input else None,
            "verification_result": self._dump(state.get("verification_result")),
            "eligibility_result": self._dump(state.get("eligibility_result")),
            "fraud_result": self._dump(state.get("fraud_result")),
            "claim_summary": self._dump(state.get("claim_summary")),
            "decision": self._dump(state.get("decision")),
            "human_review_outcome": self._dump(state.get("human_review_outcome")),
            "execution_log": state.get("execution_log", []),
        }
        return json.dumps(payload, indent=2, default=str)

    # ------------------------------------------------------------------ #
    # PDF report
    # ------------------------------------------------------------------ #
    def build_pdf_report(self, state: ClaimState) -> bytes:
        """Render a human-readable PDF summary of the claim decision.

        Raises:
            ReportServiceError: if ``fpdf2`` is not installed in the current
                environment. The caller (Streamlit UI) catches this and
                disables just the PDF download button, rather than the
                whole page failing.
        """
        try:
            from fpdf import FPDF
        except ImportError as exc:  # noqa: BLE001
            logger.error("fpdf2 is not installed; PDF report generation unavailable: %s", exc)
            raise ReportServiceError(
                "PDF generation requires the 'fpdf2' package. Install it with "
                "`pip install -r requirements.txt` (or `pip install fpdf2`) and restart the app."
            ) from exc

        claim_input = state.get("claim_input")
        decision = state.get("decision")
        summary = state.get("claim_summary")
        fraud = state.get("fraud_result")
        eligibility = state.get("eligibility_result")
        verification = state.get("verification_result")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Insurance Claim Decision Report", ln=True)

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.utcnow().isoformat()}Z", ln=True)
        if claim_input:
            pdf.cell(0, 8, f"Claim ID: {claim_input.claim_id}", ln=True)
            pdf.cell(0, 8, f"Policy Holder: {claim_input.policy.policy_holder_name}", ln=True)
            pdf.cell(0, 8, f"Claim Amount: {claim_input.claim.currency} {claim_input.claim.claim_amount:,.2f}", ln=True)

        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Decision", ln=True)
        pdf.set_font("Helvetica", "", 10)
        if decision:
            pdf.multi_cell(0, 6, f"Status: {decision.status.value}\nReason: {decision.reason}")
        else:
            pdf.multi_cell(0, 6, "No decision recorded.")

        self._section(pdf, "Document Verification", verification.summary if verification else "N/A")
        self._section(pdf, "Eligibility", eligibility.summary if eligibility else "N/A")
        self._section(
            pdf,
            "Fraud Analysis",
            f"Risk: {fraud.fraud_risk.value if fraud else 'N/A'} "
            f"(score {fraud.risk_score if fraud else 'N/A'})\n{fraud.summary if fraud else ''}",
        )
        self._section(pdf, "Executive Summary", summary.executive_summary if summary else "N/A")

        # fpdf2's output() returns a bytearray; normalize to bytes for Streamlit's download_button.
        return bytes(pdf.output())

    @staticmethod
    def _section(pdf: "FPDF", title: str, body: str) -> None:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, body or "N/A")

    @staticmethod
    def _dump(model: Any) -> Any:
        return model.model_dump(mode="json") if model is not None else None
