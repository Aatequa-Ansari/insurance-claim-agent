"""
core/config/settings.py

Centralized, typed configuration management.

Resolution order for every setting:
    1. Streamlit Secrets (``st.secrets``) -- used automatically when the
       app is running on Streamlit Community Cloud.
    2. Environment variables (populated from a local ``.env`` file via
       python-dotenv during local development).
    3. Explicit defaults defined below.

This dual-source approach is what lets the exact same codebase run both
``streamlit run app/main.py`` locally with a ``.env`` file, and on
Streamlit Community Cloud where secrets are injected via ``st.secrets``
and no ``.env`` file exists.

Usage
-----
    from core.config.settings import get_settings
    settings = get_settings()
    settings.google_api_key
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env as early as possible for local development. This is a no-op
# (and harmless) when no .env file exists, e.g. on Streamlit Cloud.
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _read_streamlit_secret(key: str) -> Optional[str]:
    """Best-effort read from ``st.secrets`` without hard-depending on Streamlit.

    Importing Streamlit is safe even outside a Streamlit runtime, but
    accessing ``st.secrets`` without a secrets.toml file raises -- so this
    is wrapped defensively and used only as a fallback source.
    """
    try:
        import streamlit as st  # local import: keep this module usable in pure-Python contexts (tests, CLI)

        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        return None
    return None


class Settings(BaseSettings):
    """Application-wide configuration, validated once at startup."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM / AI ---
    google_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Chat model name")
    gemini_embedding_model: str = Field(default="models/text-embedding-004")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_output_tokens: int = Field(default=2048, gt=0)
    llm_request_timeout_seconds: int = Field(default=60, gt=0)

    # --- Retry / resilience ---
    max_retries: int = Field(default=3, ge=0)
    retry_backoff_seconds: float = Field(default=1.5, ge=0)

    # --- Application ---
    app_name: str = Field(default="Enterprise AI Insurance Claim Processing Agent")
    environment: str = Field(default="local", description="local | staging | production")
    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="logs")
    reports_dir: str = Field(default="reports")

    # --- Business rules (also see core/config/business_rules.py for detail) ---
    high_value_claim_threshold: float = Field(
        default=500_000.0, description="Claim amount (absolute) above which human review is forced"
    )
    high_value_coverage_fraction: float = Field(
        default=0.8, description="Claim/coverage ratio above which human review is forced"
    )
    fraud_high_risk_score: float = Field(default=70.0, ge=0, le=100)
    fraud_medium_risk_score: float = Field(default=40.0, ge=0, le=100)

    @field_validator("google_api_key", mode="before")
    @classmethod
    def _fallback_to_streamlit_secret(cls, v: str) -> str:
        """If not found via env/.env, try Streamlit Secrets before failing."""
        if v:
            return v
        secret_val = _read_streamlit_secret("GOOGLE_API_KEY")
        return secret_val or v or ""

    @property
    def is_configured(self) -> bool:
        """Whether a Gemini API key is present (UI uses this to gate features)."""
        return bool(self.google_api_key)

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, process-wide :class:`Settings` instance.

    Cached via ``lru_cache`` so repeated calls (e.g. from every Streamlit
    rerun) don't re-parse the environment; call ``get_settings.cache_clear()``
    in tests if you need to reload after mutating environment variables.
    """
    return Settings()
