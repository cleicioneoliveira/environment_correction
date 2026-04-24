"""Logging helpers."""

from __future__ import annotations

import logging

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(log_level: str) -> logging.Logger:
    """Configure application logging and return the package logger."""

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )
    return logging.getLogger("environment_correction")
