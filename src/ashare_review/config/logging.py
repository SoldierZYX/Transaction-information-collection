"""Logging configuration for application entry points."""

from __future__ import annotations

import logging.config


def configure_logging(level: str = "INFO") -> None:
    """Configure concise, structured console logging without sensitive values."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                },
            },
            "root": {"handlers": ["console"], "level": level.upper()},
        }
    )
