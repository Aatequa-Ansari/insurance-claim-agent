"""
agents/document_verification_agent.py

Agent 1: Document Verification Agent.

Responsibilities (per assignment spec):
    * Verify required documents are present
    * Detect missing documents
    * Validate document completeness
    * Return structured verification

Design: completeness (which documents are required/present/missing) is
computed deterministically from ``core.config.business_rules`` -- this is
an auditable compliance check that should not depend on LLM judgment. The
LLM is used only to assess *content quality* of submitted documents and to
write the human-readable summary.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core.config.business_rules import required_documents_for
from prompts.document_verification_prompt import SYSTEM_PROMPT, build_user_prompt
from schemas.claim import ClaimInput
from schemas.enums import WorkflowNode
from schemas.results import DocumentCheckItem, VerificationResult


class _VerificationNarrative(BaseModel):
    """Internal parsing target for the LLM's qualitative assessment only."""

    document_checks: list[DocumentCheckItem] = Field(default_factory=list)
    summary: str = ""


class DocumentVerificationAgent(BaseAgent):
    """Verifies that all documents required for a claim's type were submitted."""

    node = WorkflowNode.DOCUMENT_VERIFICATION

    def evaluate(self, claim_input: ClaimInput) -> VerificationResult:
        required = required_documents_for(claim_input.incident.claim_type)
        present_types = {doc.document_type for doc in claim_input.documents}
        missing = [doc_type for doc_type in required if doc_type not in present_types]
        is_complete = len(missing) == 0
        completeness_score = (
            100.0 * (len(required) - len(missing)) / len(required) if required else 100.0
        )

        deterministic_checks = [
            DocumentCheckItem(
                document_type=doc_type,
                is_present=doc_type in present_types,
                is_valid=doc_type in present_types,
                notes="Submitted" if doc_type in present_types else "Not submitted",
            )
            for doc_type in required
        ]

        fallback_summary = (
            "All required documents were submitted."
            if is_complete
            else f"Missing {len(missing)} required document(s): "
            f"{', '.join(d.value for d in missing)}."
        )

        context = {
            "claim_id": claim_input.claim_id,
            "claim_type": claim_input.incident.claim_type.value,
            "required_documents": [d.value for d in required],
            "submitted_documents": [
                {
                    "document_type": doc.document_type.value,
                    "file_name": doc.file_name,
                    "extracted_text_excerpt": doc.extracted_text[:1500],
                }
                for doc in claim_input.documents
            ],
            "missing_documents": [d.value for d in missing],
        }

        narrative = self._safe_llm_narrative(
            SYSTEM_PROMPT,
            build_user_prompt(context),
            _VerificationNarrative,
            fallback={"document_checks": [], "summary": fallback_summary},
        )

        # Merge: prefer LLM's quality notes when available, otherwise deterministic checks.
        final_checks = narrative.document_checks or deterministic_checks
        summary = narrative.summary or fallback_summary

        return VerificationResult(
            is_complete=is_complete,
            required_documents=required,
            missing_documents=missing,
            document_checks=final_checks,
            completeness_score=round(completeness_score, 2),
            summary=summary,
        )
