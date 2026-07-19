"""
app/components/upload_widget.py

Renders the PDF upload widget for claim supporting documents, extracts
text via ``DocumentService``, and shows a classified preview list.
"""

from __future__ import annotations

import streamlit as st

from core.services.document_service import DocumentService
from core.utils.validators import ValidationError
from schemas.claim import UploadedDocument


def render_upload_widget() -> list[UploadedDocument]:
    """Render the multi-file PDF uploader and return extracted documents."""
    st.markdown('<div class="card-title">Supporting Documents</div>', unsafe_allow_html=True)
    files = st.file_uploader(
        "Upload claim documents (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Policy schedule, ID proof, medical/police reports, invoices, incident photos, etc.",
    )

    documents: list[UploadedDocument] = []
    if not files:
        st.caption("No documents uploaded yet.")
        return documents

    service = DocumentService()
    for f in files:
        try:
            file_bytes = f.getvalue()
            doc = service.extract_document(f.name, file_bytes)
            documents.append(doc)
        except ValidationError as exc:
            st.error(f"'{f.name}': {exc}")

    if documents:
        for doc in documents:
            st.markdown(
                f"""<div style="display:flex;justify-content:space-between;align-items:center;
                     padding:8px 12px;border:1px solid #263042;border-radius:8px;margin-bottom:6px;">
                     <span>📄 {doc.file_name}</span>
                     <span class="chip chip-pending">{doc.document_type.value.replace('_',' ')}</span>
                     </div>""",
                unsafe_allow_html=True,
            )
    return documents
