"""
prompts/eligibility_prompt.py

Prompt for the narrative half of eligibility checking. Deterministic
boolean checks (policy active, within coverage period, waiting period,
max coverage) are computed in code (see agents/eligibility_agent.py) --
the LLM is asked only to explain the findings in clear underwriting
language, useful for the claim summary and for human reviewers.
"""

from __future__ import annotations

from typing import Any

from prompts.base import JSON_ONLY_INSTRUCTION, render_context

SYSTEM_PROMPT = f"""You are a senior Insurance Policy Eligibility Underwriter.

You will be given the deterministic results of an eligibility check
(policy active status, coverage period, waiting period, claim type
coverage, max coverage limit) along with the underlying policy and claim
facts. Your job is to write a clear, professional explanation of the
eligibility outcome suitable for both an internal reviewer and, if
applicable, the claimant.

{JSON_ONLY_INSTRUCTION}

Return a JSON object with exactly these fields:
{{
  "summary": "<3-5 sentence professional explanation of the eligibility outcome, referencing the specific reasons>"
}}
"""


def build_user_prompt(context: dict[str, Any]) -> str:
    return (
        "Review the following eligibility check context and produce your "
        "summary as instructed.\n\n"
        f"{render_context(context)}"
    )
