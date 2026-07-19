# Changelog

All notable changes to this project are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] -- Initial Release

### Added
- Full LangGraph `StateGraph` workflow: parallel fan-out (Document
  Verification, Eligibility Check, Fraud Detection), merge barrier, Claim
  Summary synthesis, deterministic Decision Engine, and `interrupt()`-based
  Human-in-the-Loop escalation with `InMemorySaver` checkpointing.
- Five claim-processing agents (Document Verification, Eligibility Check,
  Fraud Detection, Claim Summary, Human Approval), each backed by Google
  Gemini 2.5 Flash with a deterministic fallback path.
- Pydantic v2 schema layer for claim input, agent results, and LangGraph
  state (`schemas/`).
- Service layer: `LLMService` (Gemini wrapper with retry), `DocumentService`
  (PDF extraction + classification), `ReportService` (JSON/PDF report
  generation), `ClaimService` (workflow orchestration facade).
- Enterprise-styled Streamlit dashboard ("Underwriter's Ledger" dark theme):
  New Claim intake + upload, live evidence panels, fraud risk gauge,
  decision stamp, execution timeline, human review panel, Dashboard with
  session metrics and Mermaid workflow visualization, and Claim History.
- Five built-in demo cases covering all mandated test scenarios.
- 49-test suite: schema validation, per-agent unit tests, compiled-graph
  integration tests (including interrupt/resume), service tests, and an
  explicit five-scenario acceptance suite.
- Full documentation set: README, ARCHITECTURE, INSTALLATION, DEPLOYMENT,
  CONTRIBUTING, SECURITY, ROADMAP.

## [Unreleased]

See [ROADMAP.md](ROADMAP.md) for planned work.
