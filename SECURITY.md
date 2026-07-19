# Security Policy

## Reporting a vulnerability

This is a demonstration/portfolio project. If you discover a security
issue (e.g. a prompt-injection vector, an API key leak path, or a
dependency vulnerability), please open a **private** report rather than a
public GitHub issue:

- Preferred: GitHub's "Report a vulnerability" flow under the repository's
  **Security** tab.
- Alternative: contact the maintainer directly (see repository profile).

Please include:
- A description of the issue and potential impact
- Steps to reproduce
- Any suggested remediation

We aim to acknowledge reports within 5 business days.

## Data handling notes

- **No real personal or financial data should ever be entered into this
  application.** It is a demonstration system, not a certified or audited
  data processor.
- Uploaded documents and claim data are processed **in-memory** for the
  duration of a Streamlit session and are not persisted to a database.
  Generated JSON/PDF reports are written to the local `reports/` directory
  (gitignored) purely for the download feature.
- The `GOOGLE_API_KEY` should never be committed to source control. It is
  loaded from `.env` locally (gitignored) or from Streamlit Secrets when
  deployed. `.env.example` contains placeholders only.
- LLM prompts include claim data (incident descriptions, document excerpts)
  sent to Google's Gemini API, subject to Google's API data-use terms. Do
  not use this project with sensitive real-world data.

## Dependency security

Dependencies are pinned to minimum tested versions in `requirements.txt`.
Run `pip list --outdated` periodically and `pip-audit` (or GitHub's
Dependabot, if enabled on your fork) to check for known vulnerabilities.

## Known limitations (by design, not oversight)

- The `InMemorySaver` LangGraph checkpointer stores in-progress
  (human-review-pending) claim state in process memory only — it is lost on
  restart. This is intentional for a demo deployment; see
  [DEPLOYMENT.md](DEPLOYMENT.md) for swapping in a persistent checkpointer.
- Document classification (`core/services/document_service.py`) uses
  keyword heuristics, not OCR/ML classification — it is not a substitute
  for real document-authenticity verification.
