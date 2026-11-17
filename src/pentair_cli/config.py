"""Configuration management for the Pentair CLI.

Values are resolved in this order (highest priority first):

1. Command line options (``--host``, ``--port``, ...)
2. Environment variables (``INTELLICENTER_HOST``, ...)
3. Settings file (``$XDG_CONFIG_HOME/pentair-cli/config.toml``)
4. Built-in defaults
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

APP_NAME = "pentair-cli"
ENV_PREFIX = "INTELLICENTER_"
CONFIG_PATH_ENV = "PENTAIR_CLI_CONFIG"


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or is invalid."""


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    host: str = Field(default="127.0.0.1", description="IntelliCenter host IP")
    port: int = Field(default=6681, ge=1, le=65535, description="IntelliCenter port")
    timeout: float = Field(default=10.0, gt=0, description="Connection timeout seconds")
    log_level: str = Field(default="WARNING", description="Log level for stderr diagnostics")


SETTING_KEYS: tuple[str, ...] = tuple(Settings.model_fields)


def config_dir(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    base = env.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME


def resolve_config_path(
    explicit: str | Path | None = None, environ: Mapping[str, str] | None = None
) -> Path:
    env = os.environ if environ is None else environ
    if explicit:
        return Path(explicit).expanduser()
    if env.get(CONFIG_PATH_ENV):
        return Path(env[CONFIG_PATH_ENV]).expanduser()
    return config_dir(env) / "config.toml"


def read_config_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {path}: {e}") from e
    return {k: v for k, v in data.items() if k in SETTING_KEYS}


def read_env(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    env = os.environ if environ is None else environ
    out: dict[str, str] = {}
    for key in SETTING_KEYS:
        value = env.get(ENV_PREFIX + key.upper())
        if value not in (None, ""):
            out[key] = value
    return out


@dataclass
class LoadedSettings:
    settings: Settings
    config_path: Path
    config_exists: bool
    sources: dict[str, str] = field(default_factory=dict)


def load_settings(
    overrides: Mapping[str, Any] | None = None,
    config_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> LoadedSettings:
    """Merge defaults < file < env < CLI overrides and validate."""
    path = resolve_config_path(config_path, environ)
    layers: list[tuple[str, Mapping[str, Any]]] = [
        (f"file:{path}", read_config_file(path)),
        ("env", read_env(environ)),
        ("cli", {k: v for k, v in (overrides or {}).items() if v is not None}),
    ]
    values: dict[str, Any] = {}
    sources = {key: "default" for key in SETTING_KEYS}
    for source, layer in layers:
        for key, value in layer.items():
            values[key] = value
            sources[key] = source
    try:
        settings = Settings(**values)
    except ValidationError as e:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])} ({sources.get(str(err['loc'][0]), '?')}): "
            f"{err['msg']}"
            for err in e.errors()
        )
        raise ConfigError(f"Invalid configuration: {problems}") from e
    return LoadedSettings(
        settings=settings, config_path=path, config_exists=path.is_file(), sources=sources
    )
