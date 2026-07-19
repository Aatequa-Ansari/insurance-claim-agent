"""
core/services/claim_service.py

Facade between the Streamlit UI and the LangGraph workflow engine. This is
the ONLY module that should import ``langgraph_workflow`` from the UI
layer -- Streamlit pages call ``ClaimService`` methods and never touch the
graph directly, keeping the UI a pure presentation layer.

Two entry points:
    * ``run_claim(claim_input)``   -- starts a new workflow run
    * ``resume_claim(claim_id, outcome)`` -- resumes a paused (human-review) run

Both return a :class:`ClaimRunResult`, a small wrapper that tells the UI
whether the run is complete or paused, and carries the current state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langgraph.types import Command

from core.services.document_service import DocumentService
from core.utils.logger import get_logger
from langgraph_workflow.graph_builder import get_compiled_graph
from schemas.claim import ClaimInput
from schemas.results import HumanReviewOutcome
from schemas.state import ClaimState, new_claim_state

logger = get_logger(__name__)


@dataclass
class ClaimRunResult:
    """Outcome of invoking or resuming the claim graph once."""

    claim_id: str
    state: ClaimState
    is_paused: bool
    interrupt_payload: Optional[dict] = None


class ClaimService:
    """Orchestrates end-to-end claim processing via the LangGraph workflow."""

    def __init__(self) -> None:
        self._graph = get_compiled_graph()
        self._document_service = DocumentService()

    # ------------------------------------------------------------------ #
    # Workflow execution
    # ------------------------------------------------------------------ #
    def run_claim(self, claim_input: ClaimInput) -> ClaimRunResult:
        """Start a fresh workflow run for ``claim_input``."""
        state = new_claim_state(claim_input)
        config = self._config_for(claim_input.claim_id)
        logger.info("Starting workflow for claim %s", claim_input.claim_id)
        result = self._graph.invoke(state, config=config)
        return self._to_run_result(claim_input.claim_id, result)

    def resume_claim(self, claim_id: str, outcome: HumanReviewOutcome) -> ClaimRunResult:
        """Resume a paused (human-review) workflow run with a reviewer's decision."""
        config = self._config_for(claim_id)
        logger.info("Resuming workflow for claim %s with human outcome=%s", claim_id, outcome.approved)
        result = self._graph.invoke(Command(resume=outcome.model_dump(mode="json")), config=config)
        return self._to_run_result(claim_id, result)

    def get_state(self, claim_id: str) -> Optional[ClaimState]:
        """Fetch the current checkpointed state for a claim, if any."""
        config = self._config_for(claim_id)
        snapshot = self._graph.get_state(config)
        return snapshot.values if snapshot else None

    # ------------------------------------------------------------------ #
    # Document handling (delegates to DocumentService)
    # ------------------------------------------------------------------ #
    def process_uploaded_files(self, files: list[tuple[str, bytes]]) -> list:
        """Extract text/metadata from a list of ``(file_name, file_bytes)`` tuples."""
        return [self._document_service.extract_document(name, data) for name, data in files]

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _config_for(claim_id: str) -> dict:
        # thread_id scopes the LangGraph checkpointer to a single claim run,
        # so multiple claims can be in-flight (including paused) at once.
        return {"configurable": {"thread_id": claim_id}}

    @staticmethod
    def _to_run_result(claim_id: str, raw_result: dict) -> ClaimRunResult:
        if "__interrupt__" in raw_result:
            interrupt_obj = raw_result["__interrupt__"][0]
            return ClaimRunResult(
                claim_id=claim_id,
                state=raw_result,
                is_paused=True,
                interrupt_payload=interrupt_obj.value,
            )
        return ClaimRunResult(claim_id=claim_id, state=raw_result, is_paused=False)


_shared_service: Optional[ClaimService] = None


def get_claim_service() -> ClaimService:
    """Return a process-wide shared :class:`ClaimService` instance."""
    global _shared_service
    if _shared_service is None:
        _shared_service = ClaimService()
    return _shared_service
