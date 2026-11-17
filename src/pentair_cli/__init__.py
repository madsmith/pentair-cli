"""Pentair IntelliCenter CLI."""

from __future__ import annotations


def _detect_version() -> str:
    # 1. Installed distribution metadata (uv tool install / pip install).
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("pentair-cli")
    except PackageNotFoundError:
        pass
    # 2. File written by hatch-vcs at build time (editable/dev checkouts).
    try:
        from pentair_cli._version import __version__ as v  # type: ignore[import-not-found]

        return str(v)
    except ImportError:
        return "0.0.0+unknown"


__version__ = _detect_version()
