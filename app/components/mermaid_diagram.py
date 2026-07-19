"""
app/components/mermaid_diagram.py

Renders Mermaid diagram source as an actual visual flowchart inside
Streamlit, using mermaid.js loaded from a CDN inside an HTML component.
Streamlit's built-in ``st.code(..., language="mermaid")`` only applies
syntax highlighting to the *text* -- it does not render a diagram -- so
this component is what actually draws the graph shown in the Dashboard's
"Workflow Visualization" section.

Sizing note: ``components.html()`` renders into a *fixed-height* iframe --
Streamlit does not auto-resize raw HTML components to fit their content
(that auto-resize behavior is only available to components built with the
full streamlit-component-lib JS protocol). So instead of guessing a small
height and forcing the user to scroll inside a tiny box, this component
defaults to a generous height sized for the actual claim-processing graph
(9 nodes across ~8 vertical levels) so the whole diagram renders without
an inner scrollbar. Callers can override ``height`` if the graph grows.
"""

from __future__ import annotations

import html
import uuid

import streamlit.components.v1 as components


def render_mermaid(diagram_source: str, height: int = 900) -> None:
    """Render Mermaid diagram source as an SVG flowchart.

    Args:
        diagram_source: raw Mermaid syntax (e.g. from
            ``langgraph_workflow.graph_visualizer.get_mermaid_diagram``).
        height: pixel height of the embedded component's iframe. Defaults
            to a value generous enough for the full claim-processing graph
            to render without inner scrolling; increase if the graph grows
            materially more complex.
    """
    container_id = f"mermaid-{uuid.uuid4().hex[:8]}"
    escaped_source = html.escape(diagram_source)

    component_html = f"""
    <div id="{container_id}-wrap" style="width:100%;min-height:{height - 20}px;
         display:flex;align-items:flex-start;justify-content:center;
         overflow-x:auto;overflow-y:hidden;background:transparent;padding:10px 0;">
        <div class="mermaid" id="{container_id}">{escaped_source}</div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: "dark",
            themeVariables: {{
                background: "#0B0F17",
                primaryColor: "#1B2432",
                primaryTextColor: "#E9EDF3",
                primaryBorderColor: "#D8A94E",
                lineColor: "#8C97A8",
                secondaryColor: "#131A26",
                tertiaryColor: "#131A26"
            }},
            flowchart: {{ curve: "linear", useMaxWidth: false }}
        }});
    </script>
    """
    components.html(component_html, height=height, scrolling=True)
