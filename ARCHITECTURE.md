# Architecture

## Layered design

```
┌───────────────────────────────────────────────────────────────────┐
│  Presentation Layer -- app/                                        │
│  Streamlit pages + components. No business logic. Talks only to    │
│  ClaimService, DocumentService (via ClaimService), and              │
│  ReportService.                                                    │
├───────────────────────────────────────────────────────────────────┤
│  Service / Orchestration Layer -- core/services/                   │
│  ClaimService   -- facade over the LangGraph workflow (run/resume)  │
│  DocumentService -- PDF extraction + heuristic classification       │
│  ReportService  -- JSON/PDF report generation                       │
│  LLMService     -- Gemini client wrapper, retry, structured output  │
├───────────────────────────────────────────────────────────────────┤
│  Workflow Layer -- langgraph_workflow/                              │
│  graph_builder.py -- StateGraph topology + compilation + checkpoint │
│  nodes.py         -- thin node functions delegating to agents       │
│  edges.py         -- conditional routing (pure function of state)   │
│  graph_visualizer.py -- Mermaid export                              │
├───────────────────────────────────────────────────────────────────┤
│  Agent Layer -- agents/                                             │
│  5 agents, each: deterministic core + LLM narrative + fallback      │
├───────────────────────────────────────────────────────────────────┤
│  Domain Layer -- schemas/, prompts/, core/config/                   │
│  Pydantic models, LangGraph state, prompt templates, business rules │
└───────────────────────────────────────────────────────────────────┘
```

Dependencies point **downward only** (Dependency Inversion): the
presentation layer depends on services; services depend on the workflow
layer; the workflow layer depends on agents; agents depend on the domain
layer. No layer imports "upward." This is what makes the workflow
independently testable via `pytest` without ever starting Streamlit (see
`tests/test_workflow/`).

## Why a deterministic core + LLM narrative split?

Every agent that makes a **boolean or numeric determination that affects the
claim outcome** (is a document present? is the policy expired? what's the
fraud score?) computes that determination with plain Python logic against
`core/config/business_rules.py` and the validated `ClaimInput` — not an LLM
call. Only the **narrative explanation** (why, in plain English) is
LLM-generated.

Rationale:

1. **Auditability.** An insurance regulator (or an IIT Guwahati reviewer)
   can trace exactly why a claim was rejected without needing to trust LLM
   non-determinism.
2. **Reliability.** The workflow can run — and is tested — with zero
   configured API key. Every agent has an explicit deterministic fallback
   (`BaseAgent._safe_llm_narrative`), so a Gemini outage degrades the
   *quality of prose*, never the *correctness of the decision*.
3. **Cost & latency.** Only narrative generation touches the LLM; the
   parallel branches remain fast even under LLM rate limits.

## LangGraph state design

`schemas/state.py` defines `ClaimState` as a `TypedDict`. Parallel-branch
safety comes from each of the three concurrent nodes writing to a
**different top-level key** (`verification_result` / `eligibility_result` /
`fraud_result`) — LangGraph has no write-conflict to resolve. `execution_log`
and `errors` use an `operator.add` **reducer**, so entries appended by
concurrent branches are merged (not overwritten) when LangGraph combines
the parallel results before running `merge_results`.

## Human-in-the-loop mechanics

`langgraph_workflow/nodes.py::human_approval_node` calls LangGraph's
`interrupt(payload)`. The compiled graph carries an `InMemorySaver`
checkpointer (`graph_builder.py::get_compiled_graph`), keyed per claim via
`thread_id = claim_id`. When `interrupt()` fires:

1. `graph.invoke(...)` returns immediately with the state **as of the last
   completed superstep**, plus a `"__interrupt__"` key containing the
   payload (verification/eligibility/fraud results + reason).
2. `ClaimService.run_claim` detects this and returns a `ClaimRunResult` with
   `is_paused=True`.
3. The Streamlit "New Claim" page renders the evidence + a reviewer form,
   entirely from `st.session_state` — no polling, no background thread.
4. On submit, `ClaimService.resume_claim` calls
   `graph.invoke(Command(resume=outcome), config)` with the **same**
   `thread_id`. LangGraph resumes execution exactly at the `interrupt()`
   call, which returns the resume payload, and `human_approval_node`
   finishes normally.

This is genuine pause/resume, not a simulated one — the same mechanism
LangGraph recommends for production HITL workflows.

## Decision engine

`langgraph_workflow/nodes.py::decision_engine_node` applies the rules table
from the README in a fixed order (missing docs → ineligible → escalation
triggers → approve). It's a plain `if/elif` chain over already-computed
agent results — no LLM call — so the same inputs always produce the same
decision, which is essential for the "5 mandated scenarios" to be
reproducible in CI.

## Testing strategy

| Layer | Test location | What it proves |
|---|---|---|
| Schemas | `tests/test_validation/` | Pydantic validators reject bad input at the boundary |
| Agents | `tests/test_agents/` | Deterministic logic + fallback path per agent, in isolation |
| Services | `tests/test_services/` | LLMService error handling, document extraction, report generation |
| Workflow | `tests/test_workflow/` | Compiled graph: parallel fan-out/in, conditional routing, interrupt/resume |
| Scenarios | `tests/test_scenarios/` | All 5 mandated scenarios, through the same `ClaimService` the UI uses |

All tests run offline (no real `GOOGLE_API_KEY` required) because every
LLM call point has a deterministic fallback that the test suite exercises
directly.

## Configuration resolution order

`core/config/settings.py::Settings` resolves each value as:
`.env` (local dev, via `python-dotenv`) → `st.secrets` (Streamlit Community
Cloud) → hardcoded default. This lets the identical codebase run in both
environments with zero code changes — only the secret source differs.
