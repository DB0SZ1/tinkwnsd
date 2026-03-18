"""
Structured logging configuration.
All modules should use `from utils.logger import get_logger` and call
`logger = get_logger(__name__)`.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Produces structured log lines with ISO-8601 timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        level = record.levelname
        name = record.name
        message = record.getMessage()
        line = f"{timestamp} | {level:<8} | {name} | {message}"
        if record.exc_info and record.exc_info[0] is not None:
            line += "\n" + self.formatException(record.exc_info)
        return line


def get_logger(name: str) -> logging.Logger:
    """Return a logger with structured formatting attached."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
