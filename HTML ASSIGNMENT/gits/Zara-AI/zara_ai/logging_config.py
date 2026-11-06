"""Local rotating logging without recording conversation text."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> Path:
    """Configure the application logger and return the log file path."""
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is not set; cannot locate Zara AI logs.")
        log_directory = Path(local_app_data) / "ZaraAI" / "logs"
    else:
        log_directory = Path.home() / ".local" / "state" / "zara-ai" / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / "zara-ai.log"

    logger = logging.getLogger("zara_ai")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_048_576,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(handler)
    return log_path
