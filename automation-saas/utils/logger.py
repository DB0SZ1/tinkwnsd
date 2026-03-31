"""
Structured logging configuration.
All modules should use `from utils.logger import get_logger` and call
`logger = get_logger(__name__)`.
"""

from __future__ import annotations

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Produces structured log lines with ISO-8601 timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        log_obj = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        import json
        return json.dumps(log_obj)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with structured formatting attached."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Create logs directory if missing
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")

        # 1. Console Handler (Structured)
        c_handler = logging.StreamHandler(sys.stdout)
        c_handler.setFormatter(StructuredFormatter())
        logger.addHandler(c_handler)

        # 2. File Handler (Rotating, Plain Text for UI ease)
        f_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        f_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        f_handler.setFormatter(f_formatter)
        logger.addHandler(f_handler)

        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
