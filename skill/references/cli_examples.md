# pentair-cli Reference

`pentair-cli` provides command-specific usage via `pentair-cli <group>` or
`pentair-cli <group> <command> -h`. `pentair-cli commands --json` lists every command and parameter.

The controller address comes from `--host` / `--port` / `--timeout`, the `INTELLICENTER_HOST` /
`INTELLICENTER_PORT` / `INTELLICENTER_TIMEOUT` env vars, or `~/.config/pentair-cli/config.toml`.
The CLI never writes settings.

Every command accepts `--json`. Things can be named by `name` (case-insensitive) or `id` (e.g. `C0003`).
Prefer `id` when a name is shared.

---

## Status

```bash
pentair-cli status                       # system, pool, spa, and the circuits that are on, in one call
pentair-cli pool status                  # pool temperature, setpoint, heat mode/source, heating, pump rpm
pentair-cli spa status                   # spa temperature, setpoint, heat mode/source, heating
```

*`heat_mode` is what heating is set to do, and `heating` is true only while the heater is running.
`Heater` with `heating: false` means the water is at or above the setpoint.*

---

## Heating

```bash
pentair-cli spa set-temp 102             # set spa setpoint in the controller's unit; also sets heat mode to Heater
pentair-cli pool set-temp 29 --unit C    # give the temperature in the other unit; the CLI converts it
```

*Allowed range 40–104 °F. Check `confirmed` in the result. If it's false, re-read with `status`
instead of retrying.*

---

## Circuits

```bash
pentair-cli circuit list                 # visible circuits: name, id, type, on/off
pentair-cli circuit list --all           # also virtual (X…) and system (_…) circuits
pentair-cli circuit on "Deck Jets"       # turn a circuit on by name
pentair-cli circuit off C0003            # turn a circuit off by id
```

*The `Pool` and `Spa` circuits control circulation; confirm with the user before turning them off.*

---

## Lights

```bash
pentair-cli light list                   # lights with on/off and current color effect
pentair-cli light effects                # valid effect names and codes (no controller needed)
pentair-cli light set-effect "Pool Lights" "Party Mode"   # set a color effect (name or code, e.g. PARTY)
pentair-cli circuit on "Pool Lights"     # lights switch on/off as circuits
```

*Only lights with an effect in `light list` accept `set-effect`. Plain `Light` types are on/off only.*

---

## Inspect

```bash
pentair-cli body list                    # bodies of water (pool, spa) and their ids
pentair-cli system info                  # controller name, firmware, temperature unit
pentair-cli system summary               # object counts by kind
pentair-cli entity list --kind heaters   # any kind: pumps, heaters, sensors, valves, schedules, ...
pentair-cli entity get H0001             # one object, including raw controller attributes (debug only)
```

---

## Errors

*Exit codes: 1 invalid input or controller error · 2 usage · 3 cannot connect (ask the user for the
controller IP, retry with `--host`) · 4 unknown or ambiguous name (use the names or ids the error lists) ·
5 bad setting.*

---

## Meta

```bash
pentair-cli --version                    # installed CLI version
pentair-cli version                      # CLI and controller-library versions
pentair-cli skill install --force        # reinstall this skill (to ~/.claude/skills/pentair)
```
