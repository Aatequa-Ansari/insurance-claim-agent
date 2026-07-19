"""
core/utils/retry.py

Retry-with-backoff decorator used to wrap flaky external calls -- primarily
Gemini API calls made from agents/services, which can transiently fail on
rate limits or network hiccups.

Kept dependency-free (no ``tenacity``) to minimize the requirements.txt
footprint for a Streamlit Community Cloud deployment.
"""

from __future__ import annotations

import functools
import time
from typing import Callable, ParamSpec, TypeVar

from core.utils.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    """Raised when all retry attempts for a call have been exhausted."""


def with_retry(
    max_retries: int = 3,
    backoff_seconds: float = 1.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that retries a function call on failure with exponential backoff.

    Args:
        max_retries: number of *retry* attempts after the first try
            (total attempts = max_retries + 1).
        backoff_seconds: base delay; doubles on each subsequent retry.
        exceptions: exception types that should trigger a retry. Other
            exceptions propagate immediately.

    Raises:
        RetryExhaustedError: if every attempt fails, wrapping the last
            underlying exception.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exc: Exception | None = None
            delay = backoff_seconds
            for attempt in range(1, max_retries + 2):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001 - intentional broad catch, re-raised below
                    last_exc = exc
                    if attempt > max_retries:
                        break
                    logger.warning(
                        "%s failed on attempt %d/%d (%s); retrying in %.1fs",
                        func.__qualname__,
                        attempt,
                        max_retries + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2
            raise RetryExhaustedError(
                f"{func.__qualname__} failed after {max_retries + 1} attempts"
            ) from last_exc

        return wrapper

    return decorator
