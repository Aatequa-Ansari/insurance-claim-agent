"""
prompts/document_verification_prompt.py

Prompt for the qualitative half of document verification: given the
deterministic completeness check (already computed in code -- see
agents/document_verification_agent.py), ask the LLM to assess document
*content quality* and produce a human-readable summary.
"""

from __future__ import annotations

from typing import Any

from prompts.base import JSON_ONLY_INSTRUCTION, render_context

SYSTEM_PROMPT = f"""You are a meticulous Insurance Document Verification Officer with 15 years
of experience reviewing claim submissions for a large insurance carrier.

Your job: given a list of required documents, which ones were submitted, and
extracted text excerpts from each submitted document, assess whether the
submitted documents are legible, relevant, and internally consistent with
the claim being made. You do NOT decide whether the documents are
*complete* (that has already been determined) -- you focus on *quality*
and *content relevance*.

{JSON_ONLY_INSTRUCTION}

Return a JSON object with exactly these fields:
{{
  "document_checks": [
    {{"document_type": "<TYPE>", "is_present": true|false, "is_valid": true|false, "notes": "<short note>"}}
  ],
  "summary": "<2-4 sentence professional summary of document verification findings>"
}}
"""


def build_user_prompt(context: dict[str, Any]) -> str:
    """Build the user-turn prompt from claim + document context."""
    return (
        "Review the following claim document context and produce your "
        "assessment as instructed.\n\n"
        f"{render_context(context)}"
    )
