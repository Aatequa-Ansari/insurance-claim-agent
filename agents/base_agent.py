"""
agents/base_agent.py

Abstract base class shared by all five claim-processing agents.

Provides:
    * consistent timing + logging around each agent's ``evaluate`` call
    * a uniform pattern for calling the LLM for a *narrative* field while
      keeping *numeric / boolean* determinations rule-based in code
      (auditability -- a regulator or reviewer can trace exactly why a
      claim was flagged, independent of LLM non-determinism)
    * graceful degradation: if the LLM call fails (missing API key, rate
      limit, malformed JSON after retries), the agent falls back to a
      deterministic templated narrative rather than crashing the workflow
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional

from core.services.llm_service import LLMService, LLMServiceError, get_llm_service
from core.utils.logger import get_logger
from schemas.enums import WorkflowNode


class BaseAgent(ABC):
    """Common scaffolding for all claim-processing agents.

    Subclasses implement :meth:`evaluate`, which performs the agent's
    domain logic and returns a Pydantic result model. Subclasses use
    :meth:`_safe_llm_narrative` whenever they need an LLM-generated
    narrative field, with an explicit deterministic fallback.
    """

    node: WorkflowNode

    def __init__(self, llm_service: Optional[LLMService] = None) -> None:
        self.llm_service = llm_service or get_llm_service()
        self.logger = get_logger(f"agent.{self.__class__.__name__}")

    @abstractmethod
    def evaluate(self, *args, **kwargs):
        """Run this agent's domain logic. Implemented by each subclass."""
        raise NotImplementedError

    def timed(self, func, *args, **kwargs):
        """Run ``func`` and return ``(result, duration_ms)`` for logging."""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        return result, duration_ms

    def _safe_llm_narrative(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: type,
        fallback: dict,
    ):
        """Call the LLM for a structured narrative field; fall back safely on failure.

        Args:
            output_model: Pydantic model the LLM's JSON should be parsed into.
            fallback: dict of default field values used to construct
                ``output_model`` if the LLM call fails for any reason
                (missing key, network error, malformed JSON after retries).
        """
        try:
            return self.llm_service.generate_structured(system_prompt, user_prompt, output_model)
        except LLMServiceError as exc:
            self.logger.warning(
                "%s: LLM narrative generation failed, using deterministic fallback (%s)",
                self.__class__.__name__,
                exc,
            )
            return output_model.model_validate(fallback)
