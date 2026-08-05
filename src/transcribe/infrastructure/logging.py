"""Structured logging facility for Transcribe AI."""

from __future__ import annotations

import logging
import sys

from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: str | None = None,
) -> None:
    """Initialize structured logging across the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    if json_format:
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '{"time":"%(asctime)s", "name":"%(name)s", "level":"%(levelname)s", "message":"%(message)s"}'
        )
        handler.setFormatter(formatter)
    else:
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
            markup=True,
        )

    root_logger.addHandler(handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Retrieve a logger instance with specified name."""
    return logging.getLogger(name)
