# Contributing

Thanks for considering a contribution to Meridian Claims! This is a
portfolio/demonstration project, but it's maintained to real engineering
standards — contributions are welcome and reviewed accordingly.

## Development workflow

1. Fork the repository and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Follow [INSTALLATION.md](INSTALLATION.md) to set up your environment.
3. Make your changes.
4. Run the full test suite and ensure everything passes:
   ```bash
   pytest -q
   ```
5. Format and lint (PEP 8):
   ```bash
   python -m py_compile $(git ls-files '*.py')
   ```
6. Commit with a clear, imperative message:
   ```bash
   git commit -m "Add duplicate-claim detection against historical claims"
   ```
7. Push and open a pull request describing **what** changed and **why**.

## Code style

- **PEP 8**, enforced by convention (no auto-formatter is bundled, but
  `black`-compatible formatting is preferred).
- **Type hints** on every public function/method signature.
- **Docstrings** (Google-style) on every module, class, and non-trivial
  function — explain *why*, not just *what*, where the reasoning isn't
  obvious from the code.
- **No bare `except:`** — catch specific exceptions, or `Exception` with a
  `# noqa: BLE001` comment and a clear reason in a code comment.
- Keep the **deterministic-core / LLM-narrative split** (see
  `ARCHITECTURE.md`) when adding new agent logic: any change to a claim's
  outcome must be traceable to plain Python logic, not LLM output alone.

## Adding a new agent or node

1. Add the Pydantic result model to `schemas/results.py`.
2. Add a prompt builder to `prompts/` (system prompt + `build_user_prompt`).
3. Implement the agent in `agents/`, subclassing `BaseAgent`, with a
   deterministic fallback for every LLM call.
4. Add a node wrapper in `langgraph_workflow/nodes.py` and wire it into
   `graph_builder.py`.
5. Add unit tests in `tests/test_agents/` and, if it changes graph topology,
   integration tests in `tests/test_workflow/`.
6. Update `ARCHITECTURE.md` and the workflow diagram in `README.md`.

## Reporting bugs

Open a GitHub issue with:
- Steps to reproduce
- Expected vs. actual behavior
- Whether `GOOGLE_API_KEY` was configured (fallback-mode bugs behave
  differently from live-LLM bugs)

## Security issues

Do not open a public issue for security vulnerabilities — see
[SECURITY.md](SECURITY.md).
