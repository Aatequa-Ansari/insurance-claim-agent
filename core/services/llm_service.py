"""
core/services/llm_service.py

Thin, testable wrapper around the Gemini chat model (via
``langchain-google-genai``). Every agent depends on this service rather
than importing LangChain directly, so:

    * the LLM provider can be swapped later without touching agent code
      (Dependency Inversion),
    * retry/logging/error-handling is defined exactly once,
    * agents can be unit-tested with a fake ``LLMService``.
"""

from __future__ import annotations

from typing import Any, Optional, Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from core.config.settings import Settings, get_settings
from core.utils.logger import get_logger
from core.utils.retry import with_retry
from core.utils.validators import extract_json_from_llm_response

logger = get_logger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


class LLMServiceError(RuntimeError):
    """Raised when the LLM cannot produce a usable response after retries."""


class LLMService:
    """Encapsulates all interaction with the Gemini LLM.

    Args:
        settings: application settings; defaults to the process-wide
            cached settings if not supplied (useful for tests, which can
            inject a custom :class:`Settings` instance).
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client: Optional[ChatGoogleGenerativeAI] = None

    @property
    def client(self) -> ChatGoogleGenerativeAI:
        """Lazily-constructed Gemini chat client (avoids failing at import time)."""
        if self._client is None:
            if not self._settings.is_configured:
                raise LLMServiceError(
                    "GOOGLE_API_KEY is not configured. Set it in your .env file locally "
                    "or in Streamlit Secrets when deployed."
                )
            self._client = ChatGoogleGenerativeAI(
                model=self._settings.gemini_model,
                google_api_key=self._settings.google_api_key,
                temperature=self._settings.llm_temperature,
                max_output_tokens=self._settings.llm_max_output_tokens,
                timeout=self._settings.llm_request_timeout_seconds,
            )
        return self._client

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Generate raw text from the model for a system+user prompt pair."""

        @with_retry(
            max_retries=self._settings.max_retries,
            backoff_seconds=self._settings.retry_backoff_seconds,
            exceptions=(Exception,),
        )
        def _call() -> str:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = self.client.invoke(messages)
            content = response.content
            if not content or not isinstance(content, str):
                raise LLMServiceError("Empty or non-text response from Gemini.")
            return content

        logger.info("Calling Gemini model=%s", self._settings.gemini_model)
        try:
            return _call()
        except LLMServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - covers RetryExhaustedError from the retry decorator
            raise LLMServiceError(f"Gemini call failed: {exc}") from exc

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: Type[TModel],
    ) -> TModel:
        """Generate a response and parse/validate it into ``output_model``.

        The prompt is expected to instruct the model to return raw JSON
        (see ``prompts/`` for the exact instructions per agent). This
        method handles fenced-code-block stripping and Pydantic validation,
        raising :class:`LLMServiceError` with a clear message on failure so
        the calling agent's own retry/fallback logic can react.
        """
        try:
            raw = self.generate_text(system_prompt, user_prompt)
            data: dict[str, Any] = extract_json_from_llm_response(raw)
            return output_model.model_validate(data)
        except LLMServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - covers RetryExhaustedError and any parsing/validation failure
            logger.error("Failed to generate structured output for %s: %s", output_model.__name__, exc)
            raise LLMServiceError(
                f"Model output could not be generated/parsed into {output_model.__name__}: {exc}"
            ) from exc


_shared_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Return a process-wide shared :class:`LLMService` instance."""
    global _shared_service
    if _shared_service is None:
        _shared_service = LLMService()
    return _shared_service
