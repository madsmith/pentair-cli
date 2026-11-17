"""Logging setup.

Diagnostics always go to stderr so stdout stays clean for text/JSON results.
"""

from __future__ import annotations

import logging
import sys

from loguru import logger


def setup_logging(level: str = "WARNING") -> None:
    level = level.upper()
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan> - <level>{message}</level>",
    )
    # pyintellicenter uses stdlib logging; keep it at the same level.
    logging.basicConfig(
        level=level, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("pyintellicenter").setLevel(level)
