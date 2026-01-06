"""Logging configuration

This module provides a configure_logging() function that either writes
logs to a file (when `LOG_FILE` env var is set) or to stderr for
console/testing runs.
"""

import logging
from typing import Optional
from .config import LOG_LEVEL, LOG_FILE


def configure_logging(level: Optional[int] = None) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    if level is None:
        lvl_name = LOG_LEVEL.upper()
        level = getattr(logging, lvl_name, logging.INFO)

    root.setLevel(level)  # type: ignore[arg-type]

    fmt = "%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d: \t%(message)s"
    formatter = logging.Formatter(fmt)

    log_file = LOG_FILE
    if log_file:
        try:
            fh = logging.FileHandler(log_file)
            fh.setFormatter(formatter)
            root.addHandler(fh)
            return
        except Exception:
            # fallback to stderr if file can't be opened
            pass

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    root.addHandler(sh)
