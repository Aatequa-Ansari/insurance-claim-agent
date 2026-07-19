"""
core/utils/validators.py

Small, focused validation helpers shared across the service layer.
Business-object validation (dates, ranges, required fields) lives in the
Pydantic schemas themselves; this module covers cross-cutting concerns
that don't belong to a single schema: file constraints and safe JSON
extraction from LLM responses.
"""

from __future__ import annotations

import json
import re
from typing import Any

ALLOWED_UPLOAD_EXTENSIONS = {".pdf"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file


class ValidationError(ValueError):
    """Raised for validation failures that should be surfaced to the UI."""


def validate_uploaded_file(file_name: str, size_bytes: int) -> None:
    """Validate a single uploaded file's name/extension/size.

    Raises:
        ValidationError: if the file type is unsupported or too large.
    """
    lower_name = file_name.lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_UPLOAD_EXTENSIONS):
        raise ValidationError(
            f"Unsupported file type for '{file_name}'. Allowed: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}"
        )
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(
            f"'{file_name}' exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB upload limit."
        )
    if size_bytes == 0:
        raise ValidationError(f"'{file_name}' is empty.")


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json_from_llm_response(raw_text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM's raw text output.

    Handles the common cases of Gemini wrapping JSON in markdown code
    fences, or emitting leading/trailing commentary around the JSON block.

    Raises:
        ValidationError: if no valid JSON object could be parsed.
    """
    candidate = raw_text.strip()

    fence_match = _JSON_FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    # Fallback: grab the outermost { ... } span if extra prose surrounds it.
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Could not parse JSON from LLM response: {exc}") from exc
