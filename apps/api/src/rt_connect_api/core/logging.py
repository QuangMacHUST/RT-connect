"""Structured logging and conservative redaction for runtime diagnostics."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

_SENSITIVE_KEY = re.compile(
    r"(authorization|cookie|password|secret|token|database_url|api[_-]?key)", re.I
)
_DATABASE_URL = re.compile(r"([a-z0-9+]+://)[^@\s]+@", re.I)


def _redact(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in list(event_dict.items()):
        if _SENSITIVE_KEY.search(key):
            event_dict[key] = "[REDACTED]"
        elif isinstance(value, str):
            event_dict[key] = _DATABASE_URL.sub(r"\1[REDACTED]@", value)
    return event_dict


def configure_logging(level: str) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper(), force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _redact,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
