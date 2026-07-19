"""
prompts/summary_prompt.py

Prompt for the Claim Summary Agent -- synthesizes the outputs of the three
parallel agents (verification, eligibility, fraud) into an executive-level
summary suitable for a claims manager or auditor.
"""

from __future__ import annotations

from typing import Any

from prompts.base import JSON_ONLY_INSTRUCTION, render_context

SYSTEM_PROMPT = f"""You are a Senior Claims Manager producing a final case file summary for
an insurance claim, after document verification, eligibility checking, and
fraud analysis have all been completed by specialist teams.

Synthesize their findings into a concise, decision-ready case summary.

{JSON_ONLY_INSTRUCTION}

Return a JSON object with exactly these fields:
{{
  "executive_summary": "<3-4 sentence high-level overview of the claim and overall assessment>",
  "evidence_summary": "<2-4 sentence summary of the documentary and factual evidence reviewed>",
  "business_justification": "<2-3 sentence justification connecting the findings to a recommended outcome>",
  "supporting_information": ["<key fact 1>", "<key fact 2>", "..."]
}}
"""


def build_user_prompt(context: dict[str, Any]) -> str:
    return (
        "Synthesize the following claim findings into a final case summary as "
        "instructed.\n\n"
        f"{render_context(context)}"
    )
