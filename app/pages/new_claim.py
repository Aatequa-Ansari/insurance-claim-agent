"""
app/pages/new_claim.py

The core workflow page: claim intake form + document upload, workflow
execution (with an animated progress sequence), results display (all four
agent outputs + the decision stamp), the human-in-the-loop review panel
for escalated claims, and report downloads.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.agent_log_panel import (
    render_eligibility_card,
    render_fraud_card,
    render_summary_card,
    render_verification_card,
)
from app.components.claim_form import render_claim_form
from app.components.decision_card import render_decision_stamp
from app.components.sidebar import render_sidebar_brand
from app.components.status_chip import status_chip_html
from app.components.timeline import render_timeline
from app.components.upload_widget import render_upload_widget
from core.services.claim_service import get_claim_service
from core.services.report_service import ReportService, ReportServiceError
from core.utils.logger import get_logger
from schemas.claim import ClaimDetails, ClaimInput, IncidentDetails, PolicyDetails
from schemas.enums import ClaimType
from schemas.results import HumanReviewOutcome

logger = get_logger(__name__)

def _load_css() -> None:
    css_path = Path(__file__).resolve().parents[1] / "styles" / "theme.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


DEMO_CASES: dict[str, dict] = {
    "Scenario 1 -- Complete claim (Auto Approve)": dict(
        policy_number="POL-100234",
        policy_holder_name="Ananya Sharma",
        max_coverage_amount=1_000_000.0,
        waiting_period_days=0,
        claim_type=ClaimType.MOTOR.value,
        incident_location="Pune, MH",
        incident_description=(
            "Rear-end collision at a signal on FC Road; front bumper and headlight damaged. "
            "Police report and repair invoice attached."
        ),
        claim_amount=45000.0,
        previous_claims_count=0,
        _docs="full",
    ),
    "Scenario 2 -- Missing documents (Reject)": dict(
        policy_number="POL-100235",
        policy_holder_name="Rahul Verma",
        max_coverage_amount=800_000.0,
        waiting_period_days=0,
        claim_type=ClaimType.MOTOR.value,
        incident_location="Mumbai, MH",
        incident_description="Side collision while parking; door panel dented.",
        claim_amount=30000.0,
        previous_claims_count=0,
        _docs="none",
    ),
    "Scenario 3 -- Expired policy (Reject)": dict(
        policy_number="POL-100236",
        policy_holder_name="Priya Nair",
        max_coverage_amount=500_000.0,
        waiting_period_days=0,
        claim_type=ClaimType.HEALTH.value,
        incident_location="Kochi, KL",
        incident_description="Hospitalization for appendicitis surgery, 3-day stay.",
        claim_amount=120000.0,
        previous_claims_count=0,
        _docs="full",
        _policy_expired=True,
    ),
    "Scenario 4 -- Suspicious claim (Human Approval)": dict(
        policy_number="POL-100237",
        policy_holder_name="Vikram Malhotra",
        max_coverage_amount=1_000_000.0,
        waiting_period_days=0,
        claim_type=ClaimType.MOTOR.value,
        incident_location="Delhi, DL",
        incident_description="Vehicle stolen from parking lot overnight, reported to police the next morning.",
        claim_amount=850000.0,
        previous_claims_count=4,
        _docs="full",
        _fresh_policy=True,
    ),
    "Scenario 5 -- High value claim (Human Approval)": dict(
        policy_number="POL-100238",
        policy_holder_name="Sunita Rao",
        max_coverage_amount=2_000_000.0,
        waiting_period_days=0,
        claim_type=ClaimType.PROPERTY.value,
        incident_location="Bengaluru, KA",
        incident_description="Fire damage to kitchen and adjoining rooms due to electrical short circuit.",
        claim_amount=1_700_000.0,
        previous_claims_count=0,
        _docs="full",
    ),
}


def _build_claim_input(form_values: dict, documents: list) -> ClaimInput:
    policy = PolicyDetails(
        policy_number=form_values["policy_number"],
        policy_holder_name=form_values["policy_holder_name"],
        policy_start_date=form_values["policy_start_date"],
        policy_end_date=form_values["policy_end_date"],
        max_coverage_amount=form_values["max_coverage_amount"],
        waiting_period_days=form_values["waiting_period_days"],
    )
    incident = IncidentDetails(
        incident_date=form_values["incident_date"],
        incident_location=form_values["incident_location"],
        incident_description=form_values["incident_description"],
        claim_type=ClaimType(form_values["claim_type"]),
    )
    claim = ClaimDetails(
        claim_amount=form_values["claim_amount"],
        previous_claims_count=form_values["previous_claims_count"],
    )
    return ClaimInput(policy=policy, incident=incident, claim=claim, documents=documents)


def _run_workflow_with_progress(claim_input: ClaimInput):
    service = get_claim_service()
    steps = [
        "Extracting claim information...",
        "Running Document Verification, Eligibility & Fraud agents in parallel...",
        "Merging results...",
        "Generating executive claim summary...",
        "Applying decision engine rules...",
    ]
    progress = st.progress(0, text=steps[0])
    for i, label in enumerate(steps[:-1]):
        progress.progress(int((i + 1) / len(steps) * 80), text=label)
        time.sleep(0.15)
    result = service.run_claim(claim_input)
    progress.progress(100, text="Done.")
    time.sleep(0.15)
    progress.empty()
    return result


def _record_history(claim_id: str, holder: str, status: str, amount: float) -> None:
    history = st.session_state.setdefault("claim_history", [])
    existing = next((c for c in history if c["claim_id"] == claim_id), None)
    if existing:
        existing["status"] = status
    else:
        history.append({"claim_id": claim_id, "holder": holder, "status": status, "amount": amount})


def _render_results(run_result, claim_input: ClaimInput) -> None:
    state = run_result.state

    st.markdown("### Decision")
    render_decision_stamp(state["decision"])

    st.markdown("---")
    tab_evidence, tab_summary, tab_timeline, tab_reports = st.tabs(
        ["🧾 Evidence", "🧠 Executive Summary", "🕒 Timeline", "⬇️ Reports"]
    )

    with tab_evidence:
        render_verification_card(state["verification_result"])
        render_eligibility_card(state["eligibility_result"])
        render_fraud_card(state["fraud_result"])

    with tab_summary:
        if state.get("claim_summary"):
            render_summary_card(state["claim_summary"])
        else:
            st.info("No summary available.")

    with tab_timeline:
        render_timeline(state.get("execution_log", []))

    with tab_reports:
        report_service = ReportService()
        json_report = report_service.build_json_report(state)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Download JSON Report",
                data=json_report,
                file_name=f"{claim_input.claim_id}_report.json",
                mime="application/json",
                use_container_width=True,
            )
        with col2:
            try:
                pdf_report = report_service.build_pdf_report(state)
                st.download_button(
                    "⬇️ Download PDF Report",
                    data=pdf_report,
                    file_name=f"{claim_input.claim_id}_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except ReportServiceError as exc:
                st.warning(str(exc), icon="⚠️")


def _render_human_review_panel(run_result, claim_input: ClaimInput) -> None:
    payload = run_result.interrupt_payload
    st.markdown(
        f'<div class="card"><div class="card-title">Escalated for Human Review</div>'
        f'<p>{payload["reason"]}</p></div>',
        unsafe_allow_html=True,
    )

    from schemas.results import EligibilityResult, FraudResult, VerificationResult

    render_verification_card(VerificationResult.model_validate(payload["verification_result"]))
    render_eligibility_card(EligibilityResult.model_validate(payload["eligibility_result"]))
    render_fraud_card(FraudResult.model_validate(payload["fraud_result"]))

    st.markdown("### Reviewer Decision")
    with st.form("human_review_form"):
        reviewer_name = st.text_input("Reviewer Name", value="Claims Officer")
        comments = st.text_area("Comments / Justification", height=80)
        col1, col2 = st.columns(2)
        with col1:
            approve_clicked = st.form_submit_button("✅ Approve Claim", use_container_width=True)
        with col2:
            reject_clicked = st.form_submit_button("❌ Reject Claim", use_container_width=True)

    if approve_clicked or reject_clicked:
        outcome = HumanReviewOutcome(
            approved=approve_clicked, reviewer_name=reviewer_name or "Claims Officer", comments=comments
        )
        service = get_claim_service()
        resumed = service.resume_claim(claim_input.claim_id, outcome)
        st.session_state["last_run_result"] = resumed
        _record_history(
            claim_input.claim_id,
            claim_input.policy.policy_holder_name,
            resumed.state["decision"].status.value,
            claim_input.claim.claim_amount,
        )
        st.rerun()


def main() -> None:
    _load_css()
    render_sidebar_brand()

    st.markdown('<p class="brand-title">New Claim</p>', unsafe_allow_html=True)
    st.caption("Submit a claim for AI-assisted review, or load one of the five built-in demo scenarios.")

    with st.sidebar:
        st.markdown("---")
        st.markdown("**Demo Cases**")
        chosen_demo = st.selectbox("Load a demo case", ["-- none --"] + list(DEMO_CASES.keys()))
        if st.button("Load Demo Case", use_container_width=True) and chosen_demo != "-- none --":
            st.session_state["demo_prefill"] = DEMO_CASES[chosen_demo]
            st.session_state["demo_prefill_label"] = chosen_demo
            st.session_state.pop("last_run_result", None)
            st.rerun()
        if st.button("Reset Workflow", use_container_width=True, type="secondary"):
            st.session_state.pop("last_run_result", None)
            st.session_state.pop("demo_prefill", None)
            st.rerun()

    # If we already have a paused / completed run in session, show it instead of the form.
    last_run = st.session_state.get("last_run_result")
    last_claim_input = st.session_state.get("last_claim_input")

    if last_run is not None and last_claim_input is not None:
        chip = status_chip_html(last_run.state["decision"].status) if not last_run.is_paused else (
            '<span class="chip chip-review">⏳ AWAITING REVIEW</span>'
        )
        st.markdown(
            f'<p class="ledger">Claim <b>{last_claim_input.claim_id}</b> &nbsp; {chip}</p>',
            unsafe_allow_html=True,
        )
        if last_run.is_paused:
            _render_human_review_panel(last_run, last_claim_input)
        else:
            _render_results(last_run, last_claim_input)
        st.markdown("---")
        if st.button("Start a New Claim"):
            st.session_state.pop("last_run_result", None)
            st.session_state.pop("last_claim_input", None)
            st.session_state.pop("demo_prefill", None)
            st.rerun()
        return

    # Otherwise render the intake form.
    prefill_raw = st.session_state.get("demo_prefill")
    prefill = None
    documents = []
    if prefill_raw:
        from datetime import date, timedelta

        today = date.today()
        prefill = dict(prefill_raw)
        prefill["incident_date"] = today - timedelta(days=10)
        prefill["policy_start_date"] = (
            today - timedelta(days=10) if prefill_raw.get("_fresh_policy") else today - timedelta(days=730)
        )
        prefill["policy_end_date"] = (
            today - timedelta(days=30) if prefill_raw.get("_policy_expired") else today + timedelta(days=365)
        )

        if prefill_raw.get("_docs") == "full":
            from schemas.enums import DocumentType

            documents = [
                {"file_name": "policy_schedule.pdf", "document_type": DocumentType.POLICY_DOCUMENT},
                {"file_name": "id_proof.pdf", "document_type": DocumentType.IDENTITY_PROOF},
                {"file_name": "police_report.pdf", "document_type": DocumentType.POLICE_REPORT},
                {"file_name": "incident_photo.pdf", "document_type": DocumentType.INCIDENT_PHOTO},
                {"file_name": "invoice.pdf", "document_type": DocumentType.INVOICE_RECEIPT},
                {"file_name": "medical_report.pdf", "document_type": DocumentType.MEDICAL_REPORT},
            ]
        demo_label = st.session_state.get("demo_prefill_label", "")
        st.info(f"Demo case loaded: **{demo_label}** -- review and run below.")

    form_values = render_claim_form(prefill=prefill)
    uploaded_documents = render_upload_widget()

    # Merge simulated demo documents (if any) with real uploads.
    from schemas.claim import UploadedDocument

    if documents and not uploaded_documents:
        uploaded_documents = [
            UploadedDocument(
                file_name=d["file_name"],
                document_type=d["document_type"],
                extracted_text=f"Simulated content for {d['file_name']} (demo case).",
            )
            for d in documents
        ]

    if form_values is not None:
        try:
            claim_input = _build_claim_input(form_values, uploaded_documents)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Please correct the form: {exc}")
            return

        with st.spinner("Processing claim through the AI workflow..."):
            run_result = _run_workflow_with_progress(claim_input)

        st.session_state["last_run_result"] = run_result
        st.session_state["last_claim_input"] = claim_input

        if not run_result.is_paused:
            _record_history(
                claim_input.claim_id,
                claim_input.policy.policy_holder_name,
                run_result.state["decision"].status.value,
                claim_input.claim.claim_amount,
            )
        else:
            _record_history(
                claim_input.claim_id, claim_input.policy.policy_holder_name, "HUMAN_REVIEW", claim_input.claim.claim_amount
            )
        st.rerun()


if __name__ == "__main__":
    main()
