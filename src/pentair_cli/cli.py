"""Command line interface for Pentair IntelliCenter.

Discovery is progressive: running ``pentair-cli`` or any command group without a
subcommand prints that level's help (exit 0). ``pentair-cli commands`` prints the
whole tree; add ``--json`` for a machine-readable version.
"""

from __future__ import annotations

import asyncio
import json as jsonlib
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, NoReturn, TypeVar

import click

from pentair_cli import __version__
from pentair_cli.client import IntelliCenterClient
from pentair_cli.config import (
    CONFIG_PATH_ENV,
    ENV_PREFIX,
    ConfigError,
    LoadedSettings,
    load_settings,
)
from pentair_cli.tools import AmbiguousNameError, NotFoundError, entities, pool, spa, system
from pentair_cli.utils import output
from pentair_cli.utils.logging import setup_logging

T = TypeVar("T")

# Exit codes (documented in the skill and README).
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2  # click's own usage errors
EXIT_CONNECTION = 3
EXIT_NOT_FOUND = 4
EXIT_CONFIG = 5

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 100}


# --------------------------------------------------------------------------- state


@dataclass
class AppState:
    json: bool = False
    overrides: dict[str, Any] = field(default_factory=dict)
    config_path: str | None = None
    log_level: str | None = None
    _loaded: LoadedSettings | None = None

    def load(self) -> LoadedSettings:
        if self._loaded is None:
            self._loaded = load_settings(self.overrides, self.config_path)
        return self._loaded


def _state() -> AppState:
    return click.get_current_context().find_root().ensure_object(AppState)


def _set_json(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    if value:
        _state().json = True


def _set_override(ctx: click.Context, param: click.Parameter, value: Any) -> None:
    if value is not None and param.name:
        _state().overrides[param.name] = value


def _set_attr(ctx: click.Context, param: click.Parameter, value: Any) -> None:
    if value is not None and param.name:
        setattr(_state(), param.name, value)


def json_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--json",
        is_flag=True,
        expose_value=False,
        callback=_set_json,
        help="Print machine-readable JSON on stdout.",
    )(f)


def connection_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """Connection overrides, accepted both before and after the subcommand."""
    opts = [
        click.option(
            "--host", expose_value=False, callback=_set_override, help="IntelliCenter host/IP."
        ),
        click.option(
            "--port",
            type=int,
            expose_value=False,
            callback=_set_override,
            help="IntelliCenter port.",
        ),
        click.option(
            "--timeout",
            type=float,
            expose_value=False,
            callback=_set_override,
            help="Connect timeout (s).",
        ),
    ]
    for opt in reversed(opts):
        f = opt(f)
    return f


def device_command(f: Callable[..., Any]) -> Callable[..., Any]:
    """Options for leaf commands that talk to the controller."""
    return json_option(connection_options(f))


# --------------------------------------------------------------------------- output


def emit(result: Any, render: Callable[[Any], str]) -> None:
    if _state().json:
        click.echo(output.render_json(result))
    else:
        click.echo(render(result))


def fail(message: str, code: int = EXIT_ERROR, kind: str = "error") -> NoReturn:
    if _state().json:
        click.echo(
            jsonlib.dumps(
                {"ok": False, "error": message, "kind": kind}, indent=2, ensure_ascii=False
            )
        )
    else:
        click.secho(f"error: {message}", fg="red", err=True)
    sys.exit(code)


def load_or_fail() -> LoadedSettings:
    try:
        return _state().load()
    except ConfigError as e:
        fail(str(e), EXIT_CONFIG, "config")


def run[T](fn: Callable[[IntelliCenterClient], Awaitable[T]], render: Callable[[T], str]) -> None:
    """Connect using resolved settings, run ``fn``, render the result."""
    state = _state()
    loaded = load_or_fail()
    s = loaded.settings
    setup_logging(state.log_level or s.log_level)
    client = IntelliCenterClient(host=s.host, port=s.port, timeout=s.timeout)
    try:
        result = asyncio.run(fn(client))
    except ConnectionError as e:
        fail(
            f"{e} (set --host, {ENV_PREFIX}HOST, or `host` in {loaded.config_path})",
            EXIT_CONNECTION,
            "connection",
        )
    except AmbiguousNameError as e:
        fail(str(e), EXIT_NOT_FOUND, "ambiguous")
    except NotFoundError as e:
        fail(str(e), EXIT_NOT_FOUND, "not_found")
    except ValueError as e:
        fail(str(e), EXIT_ERROR, "invalid")
    except Exception as e:  # noqa: BLE001 - surface controller errors cleanly
        fail(f"{type(e).__name__}: {e}", EXIT_ERROR, "error")
    emit(result, render)


# --------------------------------------------------------------------------- groups


class OrderedGroup(click.Group):
    """Lists commands in definition order and prints help when invoked bare."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("invoke_without_command", True)
        kwargs.setdefault("context_settings", CONTEXT_SETTINGS)
        super().__init__(*args, **kwargs)

    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)

    def invoke(self, ctx: click.Context) -> Any:
        rv = super().invoke(ctx)
        if ctx.invoked_subcommand is None:
            # Bare group: progressive discovery — show this level's help, exit 0.
            click.echo(ctx.get_help())
        return rv


ROOT_EPILOG = f"""
\b
Start here:
  pentair-cli status        overview of pool, spa and active circuits
  pentair-cli <group>       show the commands in a group
  pentair-cli commands      full command tree (add --json for agents)

\b
Settings precedence: options > {ENV_PREFIX}* env vars > config file > defaults.
Config file: $XDG_CONFIG_HOME/pentair-cli/config.toml (override: --config / {CONFIG_PATH_ENV}).
Exit codes: 0 ok, 1 error, 2 usage, 3 connection, 4 not found, 5 config.
"""


@click.group(cls=OrderedGroup, epilog=ROOT_EPILOG)
@click.version_option(
    __version__, "-V", "--version", prog_name="pentair-cli", message="%(prog)s %(version)s"
)
@json_option
@connection_options
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False),
    expose_value=False,
    callback=_set_attr,
    help="Path to settings file.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    expose_value=False,
    callback=_set_attr,
    help="Diagnostics level on stderr.",
)
def cli() -> None:
    """Control a Pentair IntelliCenter pool & spa system."""


# --------------------------------------------------------------------------- rendering


def _state_label(on: bool | None) -> str:
    return "-" if on is None else ("On" if on else "Off")


def _ref_row(r: Any, **extra: Any) -> dict[str, Any]:
    return {"name": r.name, "id": r.id, "type": r.type, "state": _state_label(r.on), **extra}


def _ref_table(rows: list[Any]) -> str:
    return output.table([_ref_row(r) for r in rows], ("name", "id", "type", "state"))


def _label(name: str | None, id_: str) -> str:
    return f"{name} ({id_})" if name else id_


# --------------------------------------------------------------------------- status


def _render_body(title: str, st: Any) -> str:
    rows: dict[str, Any] = {
        "Temperature": output.temp(st.temperature, st.unit),
        "Setpoint": output.temp(st.setpoint, st.unit),
        "Heat mode": st.heat_mode or "-",
        "Heat source": _label(st.heat_source, st.heat_source_id) if st.heat_source_id else "None",
        "Heating": "Yes" if st.heating else "No",
    }
    if getattr(st, "pump_rpm", None) is not None:
        rows["Pump"] = f"{st.pump_rpm} rpm"
    return output.kv(rows, title=f"{title} ({st.id})")


def _render_overview(ov: Any) -> str:
    parts = []
    if ov.system:
        parts.append(
            f"{ov.system.name or 'IntelliCenter'}  (firmware {output.fmt(ov.system.firmware)})"
        )
    if ov.pool:
        parts.append(_render_body("Pool", ov.pool))
    if ov.spa:
        parts.append(_render_body("Spa", ov.spa))
    on = ", ".join(c.name or c.id for c in ov.circuits_on) or "none"
    parts.append(f"Circuits on: {on}")
    return "\n\n".join(parts)


@cli.command()
@device_command
def status() -> None:
    """Overview: system, pool, spa and circuits that are on."""
    run(system.get_overview, _render_overview)


# --------------------------------------------------------------------------- pool / spa


def _render_setpoint(r: Any) -> str:
    line = f"{_label(r.name, r.id)} setpoint set to {r.setpoint}°{r.unit}"
    if r.requested_unit != r.unit:
        line += f" (requested {output.fmt(r.requested)}°{r.requested_unit})"
    if r.confirmed:
        return line + " — confirmed by controller."
    reported = output.temp(r.reported_setpoint, r.unit)
    return line + f" — not yet confirmed (controller still reports {reported})."


UNIT_OPTION = click.option(
    "--unit",
    type=click.Choice(["F", "C"], case_sensitive=False),
    help="Unit of TEMPERATURE. Default: the controller's unit (as shown by status).",
)


def _body_group(name: str, label: str, get_status: Any, set_point: Any) -> click.Group:
    @cli.group(name=name, cls=OrderedGroup)
    def grp() -> None:
        pass

    grp.help = f"{label} temperature and heating."

    @grp.command("status")
    @device_command
    def _status() -> None:
        run(get_status, lambda st: _render_body(label, st))

    _status.help = f"Show {label.lower()} temperature, setpoint, heat mode/source and heating."

    @grp.command(
        "set-temp",
        epilog=(
            f"\b\nExamples:\n  pentair-cli {name} set-temp 84\n"
            f"  pentair-cli {name} set-temp 29 --unit C"
        ),
    )
    @click.argument("temperature", type=float)
    @UNIT_OPTION
    @device_command
    def _set_temp(temperature: float, unit: str | None) -> None:
        run(lambda c: set_point(c, temperature, unit), _render_setpoint)

    _set_temp.help = f"Set the {label.lower()} heating setpoint (also sets heat mode to Heater)."
    return grp


_body_group("pool", "Pool", pool.get_pool_status, pool.set_pool_setpoint)
_body_group("spa", "Spa", spa.get_spa_status, spa.set_spa_setpoint)


# --------------------------------------------------------------------------- circuits


@cli.group(cls=OrderedGroup)
def circuit() -> None:
    """Circuits (pumps, features, lights) on/off."""


@circuit.command("list")
@click.option("--all", "include_system", is_flag=True, help="Include virtual and system circuits.")
@device_command
def circuit_list(include_system: bool) -> None:
    """List circuits and whether they are on."""
    run(lambda c: entities.list_circuits(c, include_system), _ref_table)


def _render_circuit_state(r: Any) -> str:
    return f"{_label(r.name, r.id)} turned {'on' if r.on else 'off'}."


@circuit.command("on", epilog="\b\nExample:\n  pentair-cli circuit on 'Pool Light'")
@click.argument("name")
@device_command
def circuit_on(name: str) -> None:
    """Turn circuit NAME (name or ID) on."""
    run(lambda c: entities.set_circuit_state(c, name, True), _render_circuit_state)


@circuit.command("off", epilog="\b\nExample:\n  pentair-cli circuit off C0003")
@click.argument("name")
@device_command
def circuit_off(name: str) -> None:
    """Turn circuit NAME (name or ID) off."""
    run(lambda c: entities.set_circuit_state(c, name, False), _render_circuit_state)


# --------------------------------------------------------------------------- lights


@cli.group(cls=OrderedGroup)
def light() -> None:
    """Lights and color effects."""


@light.command("list")
@device_command
def light_list() -> None:
    """List lights, whether they are on, and their color effect."""
    run(
        entities.list_lights,
        lambda rows: output.table(
            [_ref_row(r, effect=r.effect) for r in rows], ("name", "id", "type", "state", "effect")
        ),
    )


@light.command("effects")
@json_option
def light_effects() -> None:
    """List the color effects accepted by `light set-effect`."""
    emit(entities.available_light_effects(), lambda rows: output.table(rows, ("name", "code")))


@light.command(
    "set-effect",
    epilog=(
        "\b\nExamples:\n  pentair-cli light set-effect 'Pool Lights' 'Party Mode'\n"
        "  pentair-cli light set-effect C0009 caribbean"
    ),
)
@click.argument("name")
@click.argument("effect")
@device_command
def light_set_effect(name: str, effect: str) -> None:
    """Set light NAME to EFFECT (name or code; see `pentair-cli light effects`)."""
    try:
        entities.resolve_effect(effect)  # validate before connecting
    except NotFoundError as e:
        fail(str(e), EXIT_NOT_FOUND, "not_found")
    run(
        lambda c: entities.set_light_effect(c, name, effect),
        lambda r: f"{_label(r.name, r.id)} set to {r.effect}.",
    )


# --------------------------------------------------------------------------- system / entities


@cli.group(name="system", cls=OrderedGroup)
def system_group() -> None:
    """Controller information and object counts."""


@system_group.command("info")
@device_command
def system_info() -> None:
    """Controller name, firmware, temperature unit and IDs."""
    run(
        system.get_system_info,
        lambda i: output.kv(
            {
                "Name": i.name,
                "Firmware": i.firmware,
                "Unit": f"°{i.unit}" if i.unit else None,
                "ID": i.id,
                "Unique ID": i.unique_id,
            }
        ),
    )


@system_group.command("summary")
@device_command
def system_summary() -> None:
    """Number of controller objects, by kind."""
    run(system.get_model_summary, lambda s: output.kv(s.by_kind, title=f"{s.total} objects"))


@cli.group(cls=OrderedGroup)
def body() -> None:
    """Bodies of water (pool, spa)."""


@body.command("list")
@device_command
def body_list() -> None:
    """List bodies of water."""
    run(entities.list_bodies, _ref_table)


@cli.group(cls=OrderedGroup)
def entity() -> None:
    """Any controller object: list by kind, inspect by name or ID."""


def _render_entities(groups: dict[str, list[Any]]) -> str:
    sections = [
        f"{kind.replace('_', ' ').capitalize()} ({len(rows)})\n{_ref_table(rows)}"
        for kind, rows in groups.items()
        if rows
    ]
    return "\n\n".join(sections) or "(none)"


@entity.command(
    "list",
    epilog=(
        "\b\nKinds: bodies, circuits, circuit_groups, lights, light_shows,\n"
        "  color_lights, color_light_groups, pumps, heaters, sensors,\n"
        "  chem_controllers, schedules, valves"
    ),
)
@click.option("--kind", help="Only show one kind (e.g. pumps, heaters).")
@device_command
def entity_list(kind: str | None) -> None:
    """List all entities grouped by kind."""
    run(lambda c: entities.list_entities(c, kind), _render_entities)


@entity.command("get", epilog="\b\nExample:\n  pentair-cli entity get B1101")
@click.argument("name")
@device_command
def entity_get(name: str) -> None:
    """Show object NAME (name or ID), including its raw controller attributes."""

    def render(d: Any) -> str:
        head = output.kv(
            {
                "Name": d.name,
                "ID": d.id,
                "Kind": d.kind,
                "Type": d.type,
                "State": _state_label(d.on),
            }
        )
        raw = output.kv(dict(sorted(d.attributes.items())), title="Raw attributes")
        return head + "\n\n" + raw

    run(lambda c: entities.get_object(c, name), render)


# --------------------------------------------------------------------------- skill


@cli.group(cls=OrderedGroup)
def skill() -> None:
    """Agent skill bundled with this CLI."""


@skill.command("path")
@json_option
def skill_path() -> None:
    """Print where the bundled skill lives."""
    from pentair_cli import skill as sk

    src = sk.bundled_skill_dir()
    emit({"path": str(src)}, lambda d: d["path"])


@skill.command("show")
def skill_show() -> None:
    """Print the bundled SKILL.md."""
    from pentair_cli import skill as sk

    click.echo((sk.bundled_skill_dir() / "SKILL.md").read_text(encoding="utf-8"), nl=False)


@skill.command(
    "install",
    epilog="\b\nExamples:\n  pentair-cli skill install                      # ~/.claude/skills\n"
    "  pentair-cli skill install --dest ./.claude/skills  # project-local",
)
@click.option(
    "--dest",
    type=click.Path(file_okay=False),
    default=None,
    help="Skills directory to install into. Default: ~/.claude/skills",
)
@click.option("--force", is_flag=True, help="Replace an existing installed copy.")
@json_option
def skill_install(dest: str | None, force: bool) -> None:
    """Copy the skill into an agent's skills directory."""
    from pentair_cli import skill as sk

    try:
        target = sk.install(dest, force=force)
    except FileExistsError as e:
        fail(f"{e} already exists (use --force to replace)", EXIT_ERROR, "exists")
    emit(
        {"ok": True, "path": str(target), "version": __version__},
        lambda d: f"Installed pentair skill {d['version']} to {d['path']}",
    )


# --------------------------------------------------------------------------- meta


@cli.command()
@json_option
def version() -> None:
    """CLI and controller-library versions."""
    import importlib.metadata as md

    try:
        lib = md.version("pyintellicenter")
    except md.PackageNotFoundError:  # pragma: no cover
        lib = None
    data = {"pentair_cli": __version__, "pyintellicenter": lib}
    emit(
        data,
        lambda d: output.kv(
            {"pentair-cli": d["pentair_cli"], "pyintellicenter": d["pyintellicenter"]}
        ),
    )


def _command_tree(cmd: click.Command, path: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(cmd, click.Group):
        ctx = click.Context(cmd)
        for name in cmd.list_commands(ctx):
            sub = cmd.get_command(ctx, name)
            if sub is not None and not sub.hidden:
                out.extend(_command_tree(sub, [*path, name]))
        return out
    params = []
    for p in cmd.params:
        if p.name in ("help",):
            continue
        entry: dict[str, Any] = {
            "name": p.opts[0] if isinstance(p, click.Option) else p.name,
            "kind": "option" if isinstance(p, click.Option) else "argument",
            "type": p.type.name,
            "required": p.required,
        }
        if isinstance(p.type, click.Choice):
            entry["choices"] = list(p.type.choices)
        if isinstance(p, click.Option) and p.help:
            entry["help"] = p.help
        params.append(entry)
    out.append({"command": " ".join(path), "help": cmd.get_short_help_str(80), "params": params})
    return out


@cli.command()
@json_option
def commands() -> None:
    """Every command with a one-line description."""
    tree = _command_tree(cli, ["pentair-cli"])

    def render(rows: list[dict[str, Any]]) -> str:
        width = max(len(r["command"]) for r in rows)
        lines = []
        for r in rows:
            args = " ".join(p["name"].upper() for p in r["params"] if p["kind"] == "argument")
            sig = f"{r['command']} {args}".strip()
            lines.append(f"{sig.ljust(width + 14)}{r['help']}")
        return "\n".join(lines)

    emit(tree, render)
