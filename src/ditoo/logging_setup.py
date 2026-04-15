"""Logging configuration for ditoo."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ditoo.config import LoggingConfig


def setup_logging(config: "LoggingConfig") -> None:
    """Configure logging from config."""
    logging.basicConfig(
        level=getattr(logging, config.level),
        format=config.format,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
