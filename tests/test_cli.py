"""End-to-end CLI tests (click runner, fake controller)."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from pentair_cli import __version__
from pentair_cli.cli import cli
from tests.conftest import FakeClient


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def invoke(runner, *args, **kw):
    return runner.invoke(cli, list(args), prog_name="pentair", catch_exceptions=False, **kw)


@pytest.mark.parametrize("args", [[], ["pool"], ["config"], ["entity"]])
def test_bare_groups_show_help_exit_zero(runner, args):
    r = invoke(runner, *args)
    assert r.exit_code == 0
    assert "Commands:" in r.output


def test_version(runner):
    r = invoke(runner, "--version")
    assert r.output.strip() == f"pentair {__version__}"
    data = json.loads(invoke(runner, "version", "--json").output)
    assert data["pentair_cli"] == __version__ and data["pyintellicenter"]


def test_commands_tree_json(runner):
    tree = json.loads(invoke(runner, "commands", "--json").output)
    cmds = {t["command"]: t for t in tree}
    assert "pentair spa set-temp" in cmds
    unit = next(p for p in cmds["pentair spa set-temp"]["params"] if p["name"] == "--unit")
    assert unit["choices"] == ["F", "C"]


@pytest.mark.parametrize("pos", ["before", "after"])
def test_json_flag_anywhere(runner, fake_client, pos):
    args = ["--json", "spa", "status"] if pos == "before" else ["spa", "status", "--json"]
    data = json.loads(invoke(runner, *args).output)
    assert data["body"] == "B1202" and data["unit"] == "F"


def test_text_status(runner, fake_client):
    r = invoke(runner, "status")
    assert r.exit_code == 0
    assert "Pool (B1101)" in r.output and "56°F" in r.output and "Circuits on: Spa" in r.output


def test_host_option_reaches_client(runner, monkeypatch, controller, no_sleep):
    seen = {}

    def factory(**kw):
        seen.update(kw)
        return FakeClient(controller)

    monkeypatch.setattr("pentair_cli.cli.IntelliCenterClient", factory)
    monkeypatch.setenv("INTELLICENTER_HOST", "1.1.1.1")
    invoke(runner, "pool", "status", "--host", "9.9.9.9", "--timeout", "3")
    assert seen == {"host": "9.9.9.9", "port": 6681, "timeout": 3.0}


def test_set_temp(runner, fake_client, controller):
    data = json.loads(invoke(runner, "spa", "set-temp", "100", "--json").output)
    assert data["ok"] and data["verified"] and data["temperature"] == 100


def test_ambiguous_name_exit_4(runner, fake_client, controller):
    r = invoke(runner, "circuit", "on", "Cleaner", "--json")
    assert r.exit_code == 4
    assert json.loads(r.output)["kind"] == "ambiguous"
    assert controller.calls == []


def test_connection_error_exit_3(runner, fake_client):
    fake_client["client"] = FakeClient(error=ConnectionError("Timed out"))
    r = invoke(runner, "status", "--json")
    assert r.exit_code == 3
    assert json.loads(r.output) == {
        "ok": False,
        "error": "Timed out (configure with --host or `pentair config set host <ip>`)",
        "kind": "connection",
    }


def test_bad_effect_fails_before_connecting(runner, monkeypatch):
    monkeypatch.setattr(
        "pentair_cli.cli.IntelliCenterClient", lambda **kw: pytest.fail("connected")
    )
    r = invoke(runner, "light", "set-effect", "x", "disco")
    assert r.exit_code == 4 and "Valid effects" in r.stderr


def test_config_flow(runner, tmp_path):
    path = tmp_path / "c.toml"
    assert (
        invoke(runner, "--config", str(path), "config", "init", "--host", "10.0.0.5").exit_code == 0
    )
    assert invoke(runner, "--config", str(path), "config", "init").exit_code == 5
    invoke(runner, "--config", str(path), "config", "set", "port", "7000")
    data = json.loads(invoke(runner, "--config", str(path), "config", "show", "--json").output)
    assert data["settings"]["host"] == "10.0.0.5" and data["settings"]["port"] == 7000
    assert data["sources"]["port"].startswith("file:")


def test_invalid_env_exit_5(runner, monkeypatch):
    monkeypatch.setenv("INTELLICENTER_PORT", "abc")
    r = invoke(runner, "status")
    assert r.exit_code == 5 and "port (env)" in r.stderr


def test_skill_install(runner, tmp_path):
    dest = tmp_path / "skills"
    r = invoke(runner, "skill", "install", "--dest", str(dest), "--json")
    data = json.loads(r.output)
    assert (dest / "pentair" / "SKILL.md").is_file()
    assert (dest / "pentair" / "VERSION").read_text().strip() == __version__ == data["version"]
    assert invoke(runner, "skill", "install", "--dest", str(dest)).exit_code == 1
    assert invoke(runner, "skill", "install", "--dest", str(dest), "--force").exit_code == 0


def test_skill_frontmatter(runner):
    text = invoke(runner, "skill", "show").output
    assert text.startswith("---\nname: pentair\ndescription: ")
