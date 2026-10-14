"""Console and rotating-file logging for the backend."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import Settings

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_HANDLER_TAG = "_ai_server_handler"


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
