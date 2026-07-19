# Roadmap

Planned enhancements, roughly in priority order. Contributions welcome —
see [CONTRIBUTING.md](CONTRIBUTING.md).

## Near-term

- [ ] **Persistent checkpointing** -- swap `InMemorySaver` for
      `langgraph-checkpoint-sqlite` so paused human-review claims survive
      app restarts/redeploys.
- [ ] **Real document OCR** -- integrate a proper OCR pipeline for scanned
      (image-based) PDFs; current extraction relies on embedded text layers.
- [ ] **Duplicate claim detection against history** -- currently the Fraud
      Detection agent uses `previous_claims_count` as a proxy; a real
      implementation would query a claims database for near-duplicate
      incidents within `DUPLICATE_CLAIM_WINDOW_DAYS`.
- [ ] **Authentication** -- add a login layer (e.g. `streamlit-authenticator`)
      before deploying with any non-demo data.

## Mid-term

- [ ] **RAG over policy documents** -- ground the Eligibility Check agent's
      narrative in the actual policy PDF text (via embeddings + retrieval)
      rather than only structured fields.
- [ ] **Multi-currency support** -- extend `ClaimDetails.currency` handling
      throughout the fraud/eligibility heuristics (currently INR-centric
      defaults).
- [ ] **Configurable business rules via UI** -- expose
      `core/config/business_rules.py` thresholds as an admin settings page.
- [ ] **Batch claim processing** -- accept a CSV/JSON of multiple claims and
      run the workflow across all of them, with a results table.

## Long-term

- [ ] **Postgres-backed claim history** -- replace `st.session_state`
      claim history with real persistence and multi-user support.
- [ ] **Model comparison mode** -- run the same claim through multiple
      Gemini model variants (Flash vs Pro) and compare narrative quality.
- [ ] **Explainability report** -- a dedicated "Why this decision" PDF page
      auto-generated per claim, citing the specific rule and evidence.
- [ ] **API layer** -- expose `ClaimService` via a FastAPI service so the
      workflow can be called outside Streamlit (e.g. from a real claims
      management system).
