"""
Logging configuration for SEC narrative drift scripts.

Usage:
    from sec_logging import get_logger
    logger = get_logger(__name__)
    logger.info("Processing ticker %s", ticker)
"""

import logging
import os
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get a configured logger for the given module name.

    Args:
        name: Module name (typically __name__)
        level: Optional log level override (DEBUG, INFO, WARNING, ERROR)
               Defaults to INFO, can be overridden by SEC_LOG_LEVEL env var

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Determine log level
    if level is None:
        level = os.environ.get("SEC_LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, level, logging.INFO)
    logger.setLevel(numeric_level)

    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # Use a concise format for pipeline scripts
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def configure_root_logger(level: str = "INFO") -> None:
    """Configure the root logger for all SEC scripts.

    Call this once at the start of a main script to set up
    consistent logging across all modules.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
