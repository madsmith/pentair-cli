"""Tests for configuration management."""

from __future__ import annotations

import pytest

from pentair_cli.config import (
    ConfigError,
    load_settings,
    read_config_file,
    resolve_config_path,
)


def test_defaults(tmp_path):
    loaded = load_settings()
    s = loaded.settings
    assert (s.host, s.port, s.timeout, s.log_level) == ("127.0.0.1", 6681, 10.0, "WARNING")
    assert set(loaded.sources.values()) == {"default"}
    assert loaded.config_exists is False


def test_xdg_path(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    assert resolve_config_path() == tmp_path / "cfg" / "pentair-cli" / "config.toml"


def test_path_env_and_explicit_override(tmp_path, monkeypatch):
    monkeypatch.setenv("PENTAIR_CLI_CONFIG", str(tmp_path / "env.toml"))
    assert resolve_config_path() == tmp_path / "env.toml"
    assert resolve_config_path(tmp_path / "x.toml") == tmp_path / "x.toml"


def test_precedence_cli_over_env_over_file(tmp_path, monkeypatch):
    path = tmp_path / "c.toml"
    path.write_text('host = "10.0.0.1"\nport = 1111\ntimeout = 3\n')
    monkeypatch.setenv("INTELLICENTER_PORT", "2222")
    loaded = load_settings({"timeout": 9.0}, config_path=path)
    s = loaded.settings
    assert (s.host, s.port, s.timeout) == ("10.0.0.1", 2222, 9.0)
    assert loaded.sources["host"].startswith("file:")
    assert loaded.sources["port"] == "env"
    assert loaded.sources["timeout"] == "cli"


def test_none_overrides_ignored(tmp_path):
    assert load_settings({"host": None}).settings.host == "127.0.0.1"


def test_unknown_file_keys_ignored(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text('bogus = 1\nhost = "h"\n')
    assert read_config_file(path) == {"host": "h"}


@pytest.mark.parametrize("env", [{"INTELLICENTER_PORT": "nope"}, {"INTELLICENTER_TIMEOUT": "-1"}])
def test_invalid_values_raise(monkeypatch, env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ConfigError, match="env"):
        load_settings()


def test_invalid_toml(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text("host = \n")
    with pytest.raises(ConfigError, match="Invalid TOML"):
        load_settings(config_path=path)
