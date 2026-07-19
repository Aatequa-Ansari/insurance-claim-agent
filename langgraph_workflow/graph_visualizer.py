"""
langgraph_workflow/graph_visualizer.py

Generates a Mermaid diagram of the compiled claim-processing graph, used
by both the Streamlit "Workflow Visualization" tab and the project README.
"""

from __future__ import annotations

from core.utils.logger import get_logger
from langgraph_workflow.graph_builder import get_compiled_graph

logger = get_logger(__name__)

# Static fallback: hand-written Mermaid source matching the graph topology.
# Used if LangGraph's built-in drawer is unavailable (e.g. missing optional
# graphviz/mermaid-py extras) so the UI never breaks.
STATIC_MERMAID_DIAGRAM = """graph TD
    START([START]) --> EXTRACT[Extract Claim Info]
    EXTRACT --> DOC[Document Verification Agent]
    EXTRACT --> ELIG[Eligibility Check Agent]
    EXTRACT --> FRAUD[Fraud Detection Agent]
    DOC --> MERGE{{Merge Results}}
    ELIG --> MERGE
    FRAUD --> MERGE
    MERGE --> SUMMARY[Claim Summary Agent]
    SUMMARY --> DECISION{Decision Engine}
    DECISION -->|Approved| END_APPROVE([END - Approved])
    DECISION -->|Rejected| END_REJECT([END - Rejected])
    DECISION -->|Human Review| HUMAN[Human Approval Agent]
    HUMAN --> END_HUMAN([END - Human Decision])

    classDef approve fill:#16a34a,color:#fff
    classDef reject fill:#dc2626,color:#fff
    classDef review fill:#d97706,color:#fff
    class END_APPROVE approve
    class END_REJECT reject
    class HUMAN,END_HUMAN review
"""


def get_mermaid_diagram() -> str:
    """Return Mermaid source for the compiled graph.

    Tries LangGraph's native ``draw_mermaid()`` first (reflects the actual
    compiled graph topology exactly); falls back to the static, manually
    curated diagram above if that fails for any environment reason.
    """
    try:
        compiled = get_compiled_graph()
        return compiled.get_graph().draw_mermaid()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Native Mermaid export failed (%s); using static fallback diagram.", exc)
        return STATIC_MERMAID_DIAGRAM
