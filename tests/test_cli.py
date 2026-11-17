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
    return runner.invoke(cli, list(args), prog_name="pentair-cli", catch_exceptions=False, **kw)


@pytest.mark.parametrize("args", [[], ["pool"], ["light"], ["entity"]])
def test_bare_groups_show_help_exit_zero(runner, args):
    r = invoke(runner, *args)
    assert r.exit_code == 0
    assert "Commands:" in r.output


def test_version(runner):
    r = invoke(runner, "--version")
    assert r.output.strip() == f"pentair-cli {__version__}"
    data = json.loads(invoke(runner, "version", "--json").output)
    assert data["pentair_cli"] == __version__ and data["pyintellicenter"]


def test_commands_tree_json(runner):
    tree = json.loads(invoke(runner, "commands", "--json").output)
    cmds = {t["command"]: t for t in tree}
    assert "pentair-cli spa set-temp" in cmds
    unit = next(p for p in cmds["pentair-cli spa set-temp"]["params"] if p["name"] == "--unit")
    assert unit["choices"] == ["F", "C"]


@pytest.mark.parametrize("pos", ["before", "after"])
def test_json_flag_anywhere(runner, fake_client, pos):
    args = ["--json", "spa", "status"] if pos == "before" else ["spa", "status", "--json"]
    data = json.loads(invoke(runner, *args).output)
    assert data["id"] == "B1202" and data["unit"] == "F"


def test_text_status(runner, fake_client):
    r = invoke(runner, "status")
    assert r.exit_code == 0
    assert "Pool (B1101)" in r.output and "56°F" in r.output and "Circuits on: Spa" in r.output
    assert "Heat mode    Heater" in r.output
    assert "Heat source  Gas Heater (H0001)" in r.output
    assert "Heating      No" in r.output


def test_text_status_heating_yes(runner, fake_client, controller):
    controller.heating["B1101"] = True
    assert "Heating      Yes" in invoke(runner, "pool", "status").output


def test_circuit_list_text(runner, fake_client):
    out = invoke(runner, "circuit", "list").output
    assert out.splitlines()[0].split() == ["NAME", "ID", "TYPE", "STATE"]
    assert "X0043" not in out
    assert "Cleaner     C0015  Generic" in out
    assert "X0043" in invoke(runner, "circuit", "list", "--all").output


def test_no_intellicenter_field_names_in_json(runner, fake_client):
    leaked = {"objnam", "sname", "subtype", "status", "prop_name", "sw_version", "uses_metric"}
    for args in (
        ["status"],
        ["circuit", "list"],
        ["light", "list"],
        ["body", "list"],
        ["system", "info"],
        ["entity", "list"],
    ):
        text = invoke(runner, *args, "--json").output
        keys = set()

        def walk(o):
            if isinstance(o, dict):
                keys.update(o)
                [walk(v) for v in o.values()]
            elif isinstance(o, list):
                [walk(v) for v in o]

        walk(json.loads(text))
        assert not keys & leaked, (args, keys & leaked)


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
    assert data["ok"] and data["confirmed"] and data["setpoint"] == 100


def test_ambiguous_name_exit_4(runner, fake_client, controller):
    r = invoke(runner, "circuit", "on", "Step Light", "--json")
    assert r.exit_code == 4
    assert json.loads(r.output)["kind"] == "ambiguous"
    assert controller.calls == []


def test_connection_error_exit_3(runner, fake_client, tmp_path):
    config_file = tmp_path / "xdg" / "pentair-cli" / "config.toml"
    fake_client["client"] = FakeClient(error=ConnectionError("Timed out"))
    r = invoke(runner, "status", "--json")
    assert r.exit_code == 3
    assert json.loads(r.output) == {
        "ok": False,
        "error": f"Timed out (set --host, INTELLICENTER_HOST, or `host` in {config_file})",
        "kind": "connection",
    }


def test_bad_effect_fails_before_connecting(runner, monkeypatch):
    monkeypatch.setattr(
        "pentair_cli.cli.IntelliCenterClient", lambda **kw: pytest.fail("connected")
    )
    r = invoke(runner, "light", "set-effect", "x", "disco")
    assert r.exit_code == 4 and "Valid effects" in r.stderr


def test_no_config_command(runner):
    assert invoke(runner, "config").exit_code == 2


def test_config_file_is_read(runner, monkeypatch, tmp_path, controller, no_sleep):
    seen = {}

    def factory(**kw):
        seen.update(kw)
        return FakeClient(controller)

    monkeypatch.setattr("pentair_cli.cli.IntelliCenterClient", factory)
    path = tmp_path / "c.toml"
    path.write_text('host = "10.0.0.5"\nport = 7000\n')
    invoke(runner, "--config", str(path), "spa", "status")
    assert (seen["host"], seen["port"]) == ("10.0.0.5", 7000)


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
