"""
core/utils/logger.py

Application-wide structured logging.

Provides a single ``get_logger(name)`` factory so every module (agents,
services, workflow nodes) logs consistently to both the console and a
rotating log file under ``logs/``. This is distinct from
``ExecutionLogEntry`` (schemas/state.py), which is the *user-facing*
audit trail rendered in the Streamlit "Agent Logs" panel -- this logger
is the *developer-facing* diagnostic trail.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED_LOGGERS: set[str] = set()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """Return a configured :class:`logging.Logger` for ``name``.

    Idempotent: calling this repeatedly with the same ``name`` (e.g. across
    Streamlit reruns) will not attach duplicate handlers.
    """
    logger = logging.getLogger(name)

    if name in _CONFIGURED_LOGGERS:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler -- best-effort; some deployment sandboxes
    # (e.g. read-only filesystems) may not allow file writes.
    try:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("File logging unavailable; continuing with console logging only.")

    _CONFIGURED_LOGGERS.add(name)
    return logger
