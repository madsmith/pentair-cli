"""Configuration management for the Pentair CLI.

Values are resolved in this order (highest priority first):

1. Command line options (``--host``, ``--port``, ...)
2. Environment variables (``INTELLICENTER_HOST``, ...)
3. Settings file (``$XDG_CONFIG_HOME/pentair-cli/config.toml``)
4. Built-in defaults
"""

from __future__ import annotations

import json
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


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    # JSON string escaping is a valid subset of TOML basic strings.
    return json.dumps(str(value))


def write_config_file(path: Path, values: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# pentair-cli settings",
        "# Precedence: CLI options > INTELLICENTER_* env > this file",
        "",
    ]
    for key in SETTING_KEYS:
        if key in values:
            lines.append(f"{key} = {_toml_value(values[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_config_value(path: Path, key: str, raw_value: str) -> Any:
    """Validate and persist a single key; returns the coerced value."""
    if key not in SETTING_KEYS:
        raise ConfigError(f"Unknown setting '{key}'. Valid keys: {', '.join(SETTING_KEYS)}")
    current = read_config_file(path)
    current[key] = raw_value
    try:
        validated = Settings(**current)
    except ValidationError as e:
        raise ConfigError(f"Invalid value for {key}: {e.errors()[0]['msg']}") from e
    coerced = getattr(validated, key)
    current[key] = coerced
    write_config_file(path, current)
    return coerced


def unset_config_value(path: Path, key: str) -> bool:
    if key not in SETTING_KEYS:
        raise ConfigError(f"Unknown setting '{key}'. Valid keys: {', '.join(SETTING_KEYS)}")
    current = read_config_file(path)
    if key not in current:
        return False
    del current[key]
    write_config_file(path, current)
    return True
