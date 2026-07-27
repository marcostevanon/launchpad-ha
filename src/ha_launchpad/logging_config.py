"""Logging configuration

This module provides a configure_logging() function that either writes
logs to a file (when `LOG_FILE` env var is set) or to stderr for
console/testing runs.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ha_launchpad.config.settings import (
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
)


def configure_logging(level: int | None = None) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    if level is None:
        lvl_name = LOG_LEVEL.upper()
        level = getattr(logging, lvl_name, logging.INFO)

    root.setLevel(level)  # type: ignore[arg-type]

    fmt = "%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d: \t%(message)s"
    formatter = logging.Formatter(fmt)

    # urllib3 warns once per retry attempt, so a single unreachable poll emits
    # several lines before our own handler reports the failure with better
    # context. Leave errors visible, drop the play-by-play.
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    log_file = LOG_FILE
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            # Rotate in-process. launchd opens its own redirect targets once at
            # spawn and never reopens them, so a rename-based rotator would
            # leave the service writing to an unlinked inode.
            fh = RotatingFileHandler(
                log_file,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            fh.setFormatter(formatter)
            root.addHandler(fh)
            return
        except OSError as exc:
            # Say so rather than silently downgrading: the previous default
            # pointed at /var/log, which a user agent cannot write, and the
            # fallback happened invisibly.
            print(
                f"warning: cannot write log file {log_file} ({exc}); using stderr",
                file=sys.stderr,
            )

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    root.addHandler(sh)
