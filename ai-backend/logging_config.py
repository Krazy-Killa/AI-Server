"""Console and rotating-file logging for the backend."""

from __future__ import annotations

import logging
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import Settings

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_HANDLER_TAG = "_ai_server_handler"
MAX_LOG_LINES = 500


def read_recent_log_lines(log_file: Path, limit: int) -> list[str]:
    """Return the newest bounded set of lines from one configured log file."""
    if not 1 <= limit <= MAX_LOG_LINES:
        raise ValueError(f"limit must be between 1 and {MAX_LOG_LINES}.")

    with log_file.open("r", encoding="utf-8", errors="replace") as stream:
        return [line.rstrip("\r\n") for line in deque(stream, maxlen=limit)]


def setup_logging(settings: Settings) -> None:
    """Configure the root logger once; safe to call again after a reload."""
    root = logging.getLogger()
    root.setLevel(settings.log_level)

    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_TAG, False):
            root.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(LOG_FORMAT)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    try:
        settings.log_directory.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                settings.log_directory / "backend.log",
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count,
                encoding="utf-8",
            )
        )
    except OSError as error:
        logging.getLogger(__name__).warning(
            "File logging disabled; cannot write to %s: %s", settings.log_directory, error
        )

    for handler in handlers:
        handler.setFormatter(formatter)
        setattr(handler, _HANDLER_TAG, True)
        root.addHandler(handler)
