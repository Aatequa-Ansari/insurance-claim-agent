"""
prompts/fraud_detection_prompt.py

Prompt for the qualitative half of fraud detection. A deterministic risk
score is computed in code from numeric heuristics (see
agents/fraud_detection_agent.py); the LLM is additionally asked to read
the free-text incident description and document excerpts to surface
*linguistic* or *narrative* red flags (vague descriptions, inconsistent
timelines, generic language) that numeric rules can't catch.
"""

from __future__ import annotations

from typing import Any

from prompts.base import JSON_ONLY_INSTRUCTION, render_context

SYSTEM_PROMPT = f"""You are an experienced Insurance Special Investigations Unit (SIU) analyst
specializing in fraud pattern detection.

You will receive claim facts, a preliminary numeric risk score derived from
rule-based heuristics, and the claimant's free-text incident description.
Read the narrative carefully for red flags: vagueness, inconsistency,
overly generic language, mismatched dates/amounts, or patterns consistent
with staged incidents. Do not be accusatory in tone -- flag *risk
indicators*, not conclusions of guilt.

{JSON_ONLY_INSTRUCTION}

Return a JSON object with exactly these fields:
{{
  "suspicious_patterns": ["<short pattern label>", "..."],
  "reasons": ["<specific reason tied to evidence>", "..."],
  "summary": "<3-5 sentence professional fraud-risk assessment>"
}}

If you find no additional narrative red flags beyond the numeric heuristics,
return empty lists for "suspicious_patterns" and a brief summary confirming
no additional concerns were found.
"""


def build_user_prompt(context: dict[str, Any]) -> str:
    return (
        "Review the following claim and preliminary fraud-risk context, then "
        "produce your assessment as instructed.\n\n"
        f"{render_context(context)}"
    )
