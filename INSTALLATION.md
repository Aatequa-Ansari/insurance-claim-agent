# Installation

## Prerequisites

- Python 3.11 or later
- A Google AI Studio account for a Gemini API key: <https://aistudio.google.com/app/apikey>
- Git

## 1. Clone the repository

```bash
git clone <your-fork-url>
cd insurance-claim-agent
```

## 2. Create a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```
GOOGLE_API_KEY=your_google_gemini_api_key_here
```

All other variables have sensible defaults (see comments in `.env.example`).
**The app runs even without a valid key** — every agent falls back to
deterministic rule-based results and templated summaries — but live Gemini
calls require a real key.

## 5. Run the app

```bash
streamlit run app/main.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`).

## 6. Run the test suite

```bash
pytest -q
```

Expected output: `49 passed`. Tests run fully offline and do not require a
configured API key.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'core'` | Run Streamlit/pytest from the project root, not from inside `app/` |
| Agents always show "fallback mode" | Confirm `GOOGLE_API_KEY` is set in `.env` and restart Streamlit (env vars are read at process start) |
| `pip install` fails on `fpdf2` / `pypdf` | Ensure you're on Python 3.11+; both are pure-Python and need no system libraries |
| Port 8501 already in use | `streamlit run app/main.py --server.port 8502` |
