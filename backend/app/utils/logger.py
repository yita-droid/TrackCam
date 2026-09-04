"""
Structured logging setup for the TrackCam backend.

Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Model loaded", extra={"model": "yolo11n.pt", "device": "cuda"})

Design notes:
- A single call to setup_logging() (done once in app.main on startup)
  configures the root logger; every module then just does get_logger(__name__).
- Secrets (DB passwords, API keys) must NEVER be passed to logger calls.
  DATABASE_URL is redacted before logging anywhere.
- JSON logging can be toggled via LOG_JSON for log-aggregator friendliness;
  plain text is easier to read during local development.
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

_CONFIGURED = False

_CREDENTIAL_PATTERN = re.compile(r"(://)([^:/@]+):([^@/]+)@")


def redact_credentials(text: str) -> str:
    """Redact user:password segments out of connection strings before logging."""
    return _CREDENTIAL_PATTERN.sub(r"\1***:***@", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Include any extra fields passed via logger.info(..., extra={...})
        standard_keys = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())
        for key, value in record.__dict__.items():
            if key not in standard_keys and key not in payload:
                payload[key] = value
        return redact_credentials(json.dumps(payload, default=str))


class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        return redact_credentials(base)


def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configure the root logger once. Safe to call multiple times (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            PlainFormatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party loggers by default; still surfaces warnings+
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "watchfiles"):
        logging.getLogger(noisy).setLevel(max(logging.WARNING, root.level))

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
