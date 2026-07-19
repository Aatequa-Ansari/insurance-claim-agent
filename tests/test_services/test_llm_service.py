"""
tests/test_services/test_llm_service.py

Unit tests for :class:`LLMService` -- validates that misconfiguration
(missing API key) surfaces as :class:`LLMServiceError` consistently,
whether called via ``generate_text`` or ``generate_structured``, and that
JSON extraction utilities handle common LLM response quirks.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from core.config.settings import Settings
from core.services.llm_service import LLMService, LLMServiceError
from core.utils.validators import ValidationError, extract_json_from_llm_response


class _DummyModel(BaseModel):
    summary: str = ""


def test_generate_text_raises_when_unconfigured():
    settings = Settings(google_api_key="", max_retries=0)
    service = LLMService(settings=settings)

    with pytest.raises(LLMServiceError):
        service.generate_text("system", "user")


def test_generate_structured_raises_llm_service_error_when_unconfigured():
    settings = Settings(google_api_key="", max_retries=0)
    service = LLMService(settings=settings)

    with pytest.raises(LLMServiceError):
        service.generate_structured("system", "user", _DummyModel)


def test_extract_json_handles_fenced_code_block():
    raw = '```json\n{"summary": "all good"}\n```'
    parsed = extract_json_from_llm_response(raw)
    assert parsed == {"summary": "all good"}


def test_extract_json_handles_surrounding_prose():
    raw = 'Here is the result: {"summary": "ok"} -- hope that helps!'
    parsed = extract_json_from_llm_response(raw)
    assert parsed == {"summary": "ok"}


def test_extract_json_raises_on_invalid_json():
    with pytest.raises(ValidationError):
        extract_json_from_llm_response("not json at all")
