---
name: pentair
description: Read and control a Pentair IntelliCenter pool/spa system with the `pentair` CLI — water temperatures, heater setpoints, circuits (pumps, features), lights and color effects. Use when the user asks about the pool or spa, wants it heated, or wants lights/pumps/features switched.
---

# Pentair IntelliCenter CLI

The `pentair` command talks to the IntelliCenter controller on the local network.
Every command accepts `--json`; **always pass `--json` and parse stdout**. Diagnostics go to stderr.

## First steps

1. `pentair --version` to confirm the CLI is installed (this skill was written for 0.1+).
2. `pentair config show --json` to check which controller host is configured.
   If `host` is still the default `127.0.0.1`, ask the user for the controller IP and run
   `pentair config set host <ip>`.
3. `pentair status --json` gives a one-shot overview: system, pool, spa, circuits that are on.

## Discovering commands

The interface is progressive. Do not guess flags; ask the CLI:

- `pentair` lists command groups. `pentair <group>` lists that group's commands.
- `pentair <group> <command> --help` shows arguments, options and examples.
- `pentair commands --json` returns the whole tree with every parameter, which is enough to plan a call.

## Common tasks

| Goal | Command |
|---|---|
| Overview | `pentair status --json` |
| Pool / spa temperature | `pentair pool status --json` / `pentair spa status --json` |
| Heat the spa to 102 | `pentair spa set-temp 102 --json` |
| Set in a specific unit | `pentair pool set-temp 29 --unit C --json` |
| What can be switched | `pentair circuit list --json` |
| Turn a feature on/off | `pentair circuit on "Spa Jets" --json` / `pentair circuit off C0003 --json` |
| Lights | `pentair light list --json`, `pentair light effects --json` |
| Light color/show | `pentair light set-effect "Pool Light" PARTY --json` |
| Inspect any object | `pentair entity get B1101 --json` |

Names can be given as the display name (`sname`, case-insensitive) or the `objnam` (for example `C0003`).
List first if you are unsure of a name. A not-found error lists the valid names.

## Results and errors

- A successful write returns `{"ok": true, ...}`. `set-temp` also returns `verified: true|false`.
  If `verified` is false, the controller had not confirmed within 5 seconds. Re-check with `status` rather than
  retrying the write.
- Temperatures are in the controller's unit, given in the `unit` field (`F` or `C`). `set-temp` without `--unit`
  uses that same unit. Setpoints outside 40–104 °F are rejected.
- `set-temp` also switches the body's heat mode to the heater.
- On failure, `--json` prints `{"ok": false, "error": "...", "kind": "..."}` and the exit code is non-zero:

| Exit | Meaning | What to do |
|---|---|---|
| 1 | Controller or validation error | Read `error` |
| 2 | Usage error (bad arguments) | Check `--help` |
| 3 | Cannot connect | Check `pentair config show`; ask the user whether the host is right |
| 4 | Name not found | Use the names listed in the error, or run a `list` command |
| 5 | Bad configuration | Fix with `pentair config set` |

## Safety

Changing setpoints, heaters, pumps and lights affects real equipment and costs energy. Make these changes only when
the user asks. Read-only commands (`status`, `list`, `get`, `info`) are always safe.

## Configuration

Precedence: command-line options (`--host`, `--port`, `--timeout`) > env vars (`INTELLICENTER_HOST`,
`INTELLICENTER_PORT`, `INTELLICENTER_TIMEOUT`, `INTELLICENTER_LOG_LEVEL`) > settings file
(`$XDG_CONFIG_HOME/pentair-cli/config.toml`; override the path with `--config` or `PENTAIR_CLI_CONFIG`) > defaults.
