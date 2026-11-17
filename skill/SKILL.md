---
name: pentair
description: Read and control a Pentair IntelliCenter pool/spa system with the `pentair-cli` command — water temperatures, heater setpoints, circuits (pumps, features), lights and color effects. Use when the user asks about the pool or spa, wants it heated, or wants lights/pumps/features switched.
metadata:
  {
    "openclaw":
      {
        "emoji": "🏊",
        "requires": {
          "bins": ["pentair-cli"],
          "env": [
            "INTELLICENTER_HOST",
            "INTELLICENTER_PORT"
          ]
        },
        "install": [
          {
            "id": "uv",
            "kind": "uv",
            "package": "pentair-cli @ git+https://github.com/madsmith/pentair-cli",
            "bins": ["pentair-cli"],
            "label": "Install pentair-cli (uv)"
          }
        ]
      }
  }
---

# Pentair IntelliCenter CLI

The `pentair-cli` command talks to the IntelliCenter controller on the local network.
Every command accepts `--json`; **always pass `--json` and parse stdout**. Diagnostics go to stderr.

## Discovering commands

The interface is progressive. Do not guess flags; ask the CLI:

- `pentair-cli` lists command groups. `pentair-cli <group>` lists that group's commands.
- `pentair-cli <group> <command> --help` shows arguments, options and examples.
- `pentair-cli commands --json` returns the whole tree with every parameter, which is enough to plan a call.

## Common tasks

Full examples with output are in [references/cli_examples.md](references/cli_examples.md).

| Goal | Command |
|---|---|
| Overview | `pentair-cli status --json` |
| Pool / spa temperature | `pentair-cli pool status --json` / `pentair-cli spa status --json` |
| Heat the spa to 102 | `pentair-cli spa set-temp 102 --json` |
| Set in a specific unit | `pentair-cli pool set-temp 29 --unit C --json` |
| What can be switched | `pentair-cli circuit list --json` |
| Turn a feature on/off | `pentair-cli circuit on "Spa Jets" --json` / `pentair-cli circuit off C0003 --json` |
| Lights | `pentair-cli light list --json`, `pentair-cli light effects --json` |
| Light color/show | `pentair-cli light set-effect "Pool Light" PARTY --json` |
| Inspect any object | `pentair-cli entity get B1101 --json` |

Refer to things by `name` (case-insensitive) or `id` (for example `C0003`). IDs are always unique; names are not.
List first if you are unsure. A not-found error lists the valid names. An ambiguous name fails with the matching
IDs; retry with one of them.

## Output fields

Every object (circuit, light, body, heater...) has the same shape:

| Field | Meaning |
|---|---|
| `id` | Unique controller ID, e.g. `C0003`, `B1101` |
| `name` | Display name, e.g. `Jets` |
| `kind` | `circuit`, `body`, `heater`, `pump`, ... |
| `type` | e.g. `Generic`, `Spa`, `IntelliBrite light`, `Group` |
| `on` | `true`/`false`, or `null` when on/off does not apply |

`circuit list` hides virtual and system circuits (IDs starting with `X` or `_`). Add `--all` to include them.
Name lookups prefer the visible circuits.

## Results and errors

- A successful write returns `{"ok": true, ...}`. `set-temp` also returns `confirmed: true|false`
  and `reported_setpoint`. If `confirmed` is false, the controller had not confirmed within 5 seconds. Re-check with `status` rather than
  retrying the write.
- Temperatures are in the controller's unit, given in the `unit` field (`F` or `C`). `set-temp` without `--unit`
  uses that same unit. Setpoints outside 40–104 °F are rejected.
- Body status has three separate heat fields. Don't conflate them:
  - `heat_mode`: what heating is configured to do (`Off`, `Heater`, `Solar Preferred`, ...).
  - `heat_source`: the selected heater (`heat_source_id`), or null when the mode is `Off`.
  - `heating`: true only while the water is actively being heated. With mode `Heater` and the water at or above
    the setpoint, `heating` is false. That is normal: heating is enabled, the water just isn't calling for heat.
- `set-temp` also switches the body's heat mode to `Heater`.
- On failure, `--json` prints `{"ok": false, "error": "...", "kind": "..."}` and the exit code is non-zero:

| Exit | Meaning | What to do |
|---|---|---|
| 1 | Controller or validation error | Read `error` |
| 2 | Usage error (bad arguments) | Check `--help` |
| 3 | Cannot connect | The error names the host it tried. Ask the user for the controller IP; pass it with `--host` |
| 4 | Name not found | Use the names listed in the error, or run a `list` command |
| 5 | Bad configuration | The error names the bad setting and where it came from; tell the user |

## Configuration

The CLI reads settings but never writes them. Setting up the controller address is the user's job. Don't create or
edit the settings file unless the user asks you to.

Precedence: command-line options (`--host`, `--port`, `--timeout`) > env vars (`INTELLICENTER_HOST`,
`INTELLICENTER_PORT`, `INTELLICENTER_TIMEOUT`, `INTELLICENTER_LOG_LEVEL`) > settings file
(`$XDG_CONFIG_HOME/pentair-cli/config.toml`; override the path with `--config` or `PENTAIR_CLI_CONFIG`) > defaults.

## References

- [references/cli_examples.md](references/cli_examples.md): one example command per task, grouped by
  status, heating, circuits, lights, inspection and errors. Read it to find the command that reads a value or
  makes a change.

