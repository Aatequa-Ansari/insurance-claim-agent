"""
core/services/document_service.py

Handles extraction of text from uploaded PDF claim documents and a
lightweight heuristic classification into ``DocumentType``.

Uses ``pypdf`` for extraction -- pure-Python, no system dependencies,
which matters for a Streamlit Community Cloud deployment where we can't
install OS-level packages like poppler.
"""

from __future__ import annotations

import io

from pypdf import PdfReader

from core.utils.logger import get_logger
from core.utils.validators import validate_uploaded_file
from schemas.claim import UploadedDocument
from schemas.enums import DocumentType

logger = get_logger(__name__)

_CLASSIFICATION_KEYWORDS: dict[DocumentType, list[str]] = {
    DocumentType.POLICY_DOCUMENT: ["policy schedule", "policy document", "sum insured", "policy number"],
    DocumentType.IDENTITY_PROOF: ["passport", "aadhaar", "driver's license", "driving licence", "national id"],
    DocumentType.MEDICAL_REPORT: ["diagnosis", "physician", "hospital", "medical report", "discharge summary"],
    DocumentType.POLICE_REPORT: ["fir", "police report", "first information report", "police station"],
    DocumentType.INVOICE_RECEIPT: ["invoice", "receipt", "amount paid", "bill no", "total due"],
    DocumentType.INCIDENT_PHOTO: ["photo evidence", "image capture", "photograph"],
}


class DocumentService:
    """Extracts and classifies text content from uploaded claim documents."""

    def extract_document(self, file_name: str, file_bytes: bytes) -> UploadedDocument:
        """Parse a PDF's bytes into an :class:`UploadedDocument`.

        Args:
            file_name: original uploaded file name (used for validation and display).
            file_bytes: raw PDF content.

        Raises:
            ValidationError: if the file fails size/type validation.
        """
        validate_uploaded_file(file_name, len(file_bytes))

        text_chunks: list[str] = []
        page_count = 0
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
            for page in reader.pages:
                extracted = page.extract_text() or ""
                if extracted.strip():
                    text_chunks.append(extracted)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse PDF '%s': %s", file_name, exc)
            # Degrade gracefully: still register the document, flagged as unreadable.
            text_chunks = []

        full_text = "\n".join(text_chunks).strip()
        doc_type = self._classify(full_text)

        logger.info(
            "Extracted document '%s': %d page(s), %d chars, classified as %s",
            file_name,
            page_count,
            len(full_text),
            doc_type.value,
        )

        return UploadedDocument(
            file_name=file_name,
            document_type=doc_type,
            extracted_text=full_text,
            page_count=page_count,
            size_bytes=len(file_bytes),
        )

    @staticmethod
    def _classify(text: str) -> DocumentType:
        """Heuristic keyword-based document classification.

        This is intentionally simple (not LLM-based) so document typing is
        instant and free; the Document Verification Agent can still use
        the LLM to *validate* content quality on top of this coarse type.
        """
        lowered = text.lower()
        for doc_type, keywords in _CLASSIFICATION_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return doc_type
        return DocumentType.OTHER
