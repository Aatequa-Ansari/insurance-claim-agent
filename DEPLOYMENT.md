# Deployment

## Deploying to GitHub

1. Create a new (empty) repository on GitHub.
2. From the project root:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Enterprise AI Insurance Claim Processing Agent"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
3. Confirm `.env` was **not** committed (it's excluded via `.gitignore`) —
   only `.env.example` should be tracked.

## Deploying to Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. Click **New app**, select your repository, branch `main`, and set the
   main file path to:
   ```
   app/main.py
   ```
3. Under **Advanced settings → Secrets**, paste your configuration in TOML
   format (mirrors `.env.example`):
   ```toml
   GOOGLE_API_KEY = "your_google_gemini_api_key_here"
   GEMINI_MODEL = "gemini-2.5-flash"
   ENVIRONMENT = "production"
   ```
   `core/config/settings.py` automatically reads from `st.secrets` when no
   `.env` file is present, so no code changes are needed between local and
   cloud deployment.
4. Click **Deploy**. The first build installs `requirements.txt`
   (pure-Python dependencies only — no system packages required, so the
   default Streamlit Cloud image works unmodified).
5. Once live, verify:
   - The sidebar does **not** show the "GOOGLE_API_KEY not set" warning.
   - **New Claim → Load Demo Case → Scenario 1** produces an `APPROVED`
     stamp.
   - **New Claim → Load Demo Case → Scenario 5** pauses for human review and
     resumes correctly after clicking Approve/Reject.

## Environment parity

| Setting source | Local dev | Streamlit Community Cloud |
|---|---|---|
| `GOOGLE_API_KEY` | `.env` file | App Settings → Secrets |
| Logs | `logs/app.log` (rotating file) + console | Console only (ephemeral filesystem) |
| Session state | Per browser tab, in-process | Per browser tab, per app instance |
| LangGraph checkpointer | `InMemorySaver` (process memory) | `InMemorySaver` (resets on app restart/redeploy) |

> **Note on persistence:** the in-memory checkpointer means paused
> (human-review) claims are lost if the Streamlit process restarts or
> redeploys. For a real production deployment, swap `InMemorySaver` for a
> persistent checkpointer (e.g. `langgraph-checkpoint-sqlite` or
> `langgraph-checkpoint-postgres`) in `langgraph_workflow/graph_builder.py` —
> the rest of the codebase (nodes, service layer, UI) requires no changes.

## Updating a live deployment

Streamlit Community Cloud auto-redeploys on every push to the configured
branch. To roll out a change:

```bash
git add .
git commit -m "Describe your change"
git push
```

The app rebuilds automatically; watch the deployment logs in the Streamlit
Cloud dashboard for any dependency or import errors.
