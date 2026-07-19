"""
langgraph_workflow/graph_builder.py

Builds and compiles the claim-processing ``StateGraph``.

Graph shape
-----------
::

    START
      -> extract_claim_info
           -> document_verification   \\
           -> eligibility_check        }-> merge_results -> claim_summary -> decision_engine
           -> fraud_detection         /
    decision_engine --(conditional)--> human_approval -> END
    decision_engine --(conditional)--> END

``document_verification``, ``eligibility_check`` and ``fraud_detection``
all have ``extract_claim_info`` as their sole predecessor and
``merge_results`` as their sole successor -- LangGraph therefore executes
them concurrently and waits for all three before running ``merge_results``
(true parallel fan-out / fan-in, not sequential simulation).

A checkpointer (``InMemorySaver``) is attached so the graph supports
``interrupt()`` / ``Command(resume=...)`` for the Human-in-the-Loop node.
Each claim run uses its own ``thread_id`` (the claim ID), so multiple
claims can be paused independently within one Streamlit session.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from langgraph_workflow.edges import route_after_decision
from langgraph_workflow.nodes import (
    claim_summary_node,
    decision_engine_node,
    document_verification_node,
    eligibility_check_node,
    extract_claim_info_node,
    fraud_detection_node,
    human_approval_node,
    merge_results_node,
)
from schemas.enums import WorkflowNode
from schemas.state import ClaimState


def build_graph() -> StateGraph:
    """Construct the (uncompiled) claim-processing graph definition."""
    graph = StateGraph(ClaimState)

    graph.add_node(WorkflowNode.EXTRACT_CLAIM_INFO.value, extract_claim_info_node)
    graph.add_node(WorkflowNode.DOCUMENT_VERIFICATION.value, document_verification_node)
    graph.add_node(WorkflowNode.ELIGIBILITY_CHECK.value, eligibility_check_node)
    graph.add_node(WorkflowNode.FRAUD_DETECTION.value, fraud_detection_node)
    graph.add_node(WorkflowNode.MERGE_RESULTS.value, merge_results_node)
    graph.add_node(WorkflowNode.CLAIM_SUMMARY.value, claim_summary_node)
    graph.add_node(WorkflowNode.DECISION_ENGINE.value, decision_engine_node)
    graph.add_node(WorkflowNode.HUMAN_APPROVAL.value, human_approval_node)

    graph.add_edge(START, WorkflowNode.EXTRACT_CLAIM_INFO.value)

    # Parallel fan-out: three independent branches from the same source node.
    graph.add_edge(WorkflowNode.EXTRACT_CLAIM_INFO.value, WorkflowNode.DOCUMENT_VERIFICATION.value)
    graph.add_edge(WorkflowNode.EXTRACT_CLAIM_INFO.value, WorkflowNode.ELIGIBILITY_CHECK.value)
    graph.add_edge(WorkflowNode.EXTRACT_CLAIM_INFO.value, WorkflowNode.FRAUD_DETECTION.value)

    # Fan-in: merge_results waits for all three branches.
    graph.add_edge(WorkflowNode.DOCUMENT_VERIFICATION.value, WorkflowNode.MERGE_RESULTS.value)
    graph.add_edge(WorkflowNode.ELIGIBILITY_CHECK.value, WorkflowNode.MERGE_RESULTS.value)
    graph.add_edge(WorkflowNode.FRAUD_DETECTION.value, WorkflowNode.MERGE_RESULTS.value)

    graph.add_edge(WorkflowNode.MERGE_RESULTS.value, WorkflowNode.CLAIM_SUMMARY.value)
    graph.add_edge(WorkflowNode.CLAIM_SUMMARY.value, WorkflowNode.DECISION_ENGINE.value)

    graph.add_conditional_edges(
        WorkflowNode.DECISION_ENGINE.value,
        route_after_decision,
        {
            WorkflowNode.HUMAN_APPROVAL.value: WorkflowNode.HUMAN_APPROVAL.value,
            END: END,
        },
    )
    graph.add_edge(WorkflowNode.HUMAN_APPROVAL.value, END)

    return graph


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Return a process-wide compiled graph with an in-memory checkpointer.

    Cached so the graph is only built/compiled once per process. The
    checkpointer is what enables ``interrupt()``-based Human-in-the-Loop:
    without it, LangGraph cannot pause and later resume a run.
    """
    checkpointer = InMemorySaver()
    return build_graph().compile(checkpointer=checkpointer)
