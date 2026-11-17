# Pentair IntelliCenter CLI

Command line interface for controlling Pentair IntelliCenter pool and spa systems.
It is the CLI counterpart of [pentair-mcp](../pentair-mcp) and ships with an agent skill
(`skill/SKILL.md`), so coding agents can drive it directly.

## Features

- Read pool/spa temperatures, setpoints and heater state (`pentair status`)
- Set heating setpoints, switch circuits, set light effects
- Inspect the controller object model
- Human-readable text by default, `--json` on every command
- Progressive discovery: `pentair`, then `pentair <group>`, then `pentair <group> <cmd> --help`

## Install

```bash
uv tool install .                # or: uv tool install git+<repo-url>
pentair --version                # -> pentair 0.1.0
pentair version                  # CLI, library and Python versions, install path
pentair skill install            # copies the skill to ~/.claude/skills/pentair
```

The version comes from git tags via `hatch-vcs` (tag `v0.1.0` → `0.1.0`). An untagged or dirty
checkout reports a dev version such as `0.1.1.dev3+g1a2b3c4`, so you can tell which build is installed.
`pentair skill install` writes a `VERSION` file next to the installed `SKILL.md`.

## Usage

```text
$ pentair
Usage: pentair [OPTIONS] COMMAND [ARGS]...

Commands:
  status    Overview: system, pool, spa and circuits that are on.
  pool      Pool temperature and heater.
  spa       Spa temperature and heater.
  circuit   Circuits (pumps, features, lights) on/off.
  light     Lights and color effects.
  system    Controller information and object model.
  body      Bodies of water (pool, spa).
  entity    Any controller object: list by kind, inspect by name.
  config    Show and edit settings (file, env, defaults).
  skill     Agent skill bundled with this CLI.
  version   Detailed version info (CLI, Python, library, install path).
  commands  Every command with a one-line description.
```

```bash
pentair status
pentair spa set-temp 102
pentair pool set-temp 29 --unit C
pentair circuit on "Spa Jets"
pentair light set-effect "Pool Light" PARTY
pentair entity get B1101 --json
pentair commands --json          # full machine-readable command tree
```

`--json`, `--host`, `--port` and `--timeout` work before or after the subcommand.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | Controller or validation error |
| 2 | Usage error |
| 3 | Cannot connect |
| 4 | Name not found |
| 5 | Bad configuration |

With `--json`, errors are printed on stdout as `{"ok": false, "error": "...", "kind": "..."}`.

## Configuration

Precedence (highest first):

1. Options: `--host`, `--port`, `--timeout`, `--log-level`
2. Environment: `INTELLICENTER_HOST`, `INTELLICENTER_PORT`, `INTELLICENTER_TIMEOUT`, `INTELLICENTER_LOG_LEVEL`
3. Settings file: `$XDG_CONFIG_HOME/pentair-cli/config.toml` (default `~/.config/pentair-cli/config.toml`).
   Override the path with `--config PATH` or `PENTAIR_CLI_CONFIG`.
4. Defaults

```bash
pentair config init --host 10.0.0.144
pentair config set timeout 5
pentair config show              # effective values and where each came from
```

See `config.example.toml`.

## Project Layout

```
pentair-cli/
├── skill/SKILL.md               # agent skill (bundled into the wheel)
├── src/pentair_cli/
│   ├── __init__.py              # __version__ (from package metadata / hatch-vcs)
│   ├── __main__.py
│   ├── cli.py                   # click command tree (≈ server.py in pentair-mcp)
│   ├── config.py                # CLI > env > XDG TOML > defaults
│   ├── client.py
│   ├── skill.py                 # locate/install bundled skill
│   ├── tools/                   # same operations as pentair-mcp's tools/
│   │   ├── body.py  pool.py  spa.py  system.py  entities.py  common.py
│   ├── models/schemas.py
│   └── utils/{logging,output}.py
└── tests/
```

## Development

```bash
uv sync --extra dev
uv run pentair --help
uv run pytest
```

## Releasing

```bash
git tag v0.1.0 && uv build        # dist/pentair_cli-0.1.0-*.whl
```
