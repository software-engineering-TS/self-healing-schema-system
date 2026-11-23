"""Rotating application logging."""
import logging
import sys
from logging.handlers import RotatingFileHandler

from config import LOG_FILE, LOG_FORMAT, LOG_LEVEL


def _build_logger(name: str = "schema_healer") -> logging.Logger:
    app_logger = logging.getLogger(name)
    if app_logger.handlers:
        return app_logger
    app_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    app_logger.propagate = False
    formatter = logging.Formatter(LOG_FORMAT)
    try:
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024,
                                           backupCount=3, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        app_logger.addHandler(file_handler)
    except OSError:
        # Read-only deployments can still run with console logging.
        pass
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    app_logger.addHandler(console_handler)
    return app_logger


logger = _build_logger()