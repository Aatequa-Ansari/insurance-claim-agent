"""
tests/test_services/test_document_service.py

Unit tests for :class:`DocumentService` -- PDF extraction and heuristic
document classification.
"""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from core.services.document_service import DocumentService
from core.utils.validators import ValidationError
from schemas.enums import DocumentType


def _make_pdf_bytes(text_marker: str) -> bytes:
    """Build a minimal valid (if textless) PDF for upload-validation tests.

    Note: pypdf's writer alone can't easily embed arbitrary text content
    without a font/content stream setup, so classification-by-content is
    tested via the private ``_classify`` helper directly (see
    ``test_classification_by_keyword`` below); this helper only produces
    a structurally valid PDF for the extraction/validation path.
    """
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extract_document_returns_metadata():
    service = DocumentService()
    pdf_bytes = _make_pdf_bytes("policy schedule")

    doc = service.extract_document("policy.pdf", pdf_bytes)

    assert doc.file_name == "policy.pdf"
    assert doc.page_count == 1
    assert doc.size_bytes == len(pdf_bytes)


def test_rejects_non_pdf_extension():
    service = DocumentService()
    with pytest.raises(ValidationError):
        service.extract_document("resume.docx", b"not a pdf")


def test_rejects_empty_file():
    service = DocumentService()
    with pytest.raises(ValidationError):
        service.extract_document("empty.pdf", b"")


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ("This is the POLICY SCHEDULE for sum insured 100000", DocumentType.POLICY_DOCUMENT),
        ("Passport number A1234567", DocumentType.IDENTITY_PROOF),
        ("Hospital discharge summary, diagnosis: fracture", DocumentType.MEDICAL_REPORT),
        ("First Information Report filed at police station", DocumentType.POLICE_REPORT),
        ("Invoice #1234, amount paid: 5000", DocumentType.INVOICE_RECEIPT),
        ("random unrelated text with no keywords", DocumentType.OTHER),
    ],
)
def test_classification_by_keyword(text, expected_type):
    assert DocumentService._classify(text) == expected_type
