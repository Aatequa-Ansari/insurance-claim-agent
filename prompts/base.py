"""
prompts/base.py

Shared helpers for building agent prompts. Every agent prompt follows the
same contract: a system prompt establishing the persona + strict JSON
output instructions, and a user prompt containing the serialized claim
context. Keeping the JSON-output boilerplate in one place ensures all
five agents fail/parse consistently.
"""

from __future__ import annotations

import json
from typing import Any

JSON_ONLY_INSTRUCTION = (
    "Respond with ONLY a single valid JSON object -- no markdown code fences, "
    "no commentary before or after, no trailing text. If you are unsure of a "
    "value, make your best professional judgment; never leave a required "
    "field out."
)


def render_context(data: dict[str, Any]) -> str:
    """Render a context dict as pretty JSON for embedding in a user prompt."""
    return json.dumps(data, indent=2, default=str)
