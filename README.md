# tc002

Animated screens, a playlist that replaces the built-in carousel, and live Claude Code
status for the **Ulanzi TC002** pixel clock (52×16 RGB). Talks to the clock's stock
firmware over the LAN — no flashing, no cloud, no runtime dependencies beyond Python.

| Claude busy | Claude idle | DONE | WAIT |
|---|---|---|---|
| ![](docs/screens/claude-busy.gif) | ![](docs/screens/claude-idle.gif) | ![](docs/screens/claude-done.gif) | ![](docs/screens/claude-wait.gif) |

| System | Text | Alert | No session |
|---|---|---|---|
| ![](docs/screens/sys.gif) | ![](docs/screens/text.gif) | ![](docs/screens/alert-error.gif) | ![](docs/screens/claude-off.gif) |

## What it does

- **`claude` screen** — the spark spins while Claude Code is generating and breathes when
  idle; live sub-agents orbit it; an equalizer or heartbeat runs beside the session count.
  Claude Code hooks turn it into a green **DONE** when a turn ends and an orange **WAIT**
  when Claude needs you.
- **`sys` screen** — scrolling CPU chart of the last 52 seconds plus memory.
- **Playlist** — switches the clock between your screens and the built-in apps you keep
  (for example the clock), on your timing. The device's own carousel and every built-in
  app you did not keep are turned off, and restored by `tc002 uninstall`.
- **One-off messages** — `tc002 text` and `tc002 alert` from any script or CI job.

Every animation is rendered locally and sent as one looping GIF, so the clock animates by
itself and the screen is re-sent only when its content changes.

## Requirements

- A TC002 on stock firmware **V1.1.0+** (`tc002 doctor` checks), on the same network.
- macOS (the background service uses launchd; the screens read macOS tools).
- [uv](https://docs.astral.sh/uv/) — it installs Python 3.15 for you.

## Install

```bash
git clone https://github.com/Misoto22/tc002.git
cd tc002
uv tool install .
tc002 setup --host 192.168.1.50 --config ./tc002.toml
tc002 install
tc002 doctor
```

`setup` stores the clock's IP and the path of your `tc002.toml` in `~/.config/tc002/`.
Find the IP in Ulanzi Studio, your router's client list, or `tc002 --host <ip> info`.

`install` does three things, each also available on its own:

| Step | Command | Undo |
|---|---|---|
| Keep only the built-in apps in `device.keep_builtins`; turn off the device carousel when a playlist is set | `tc002 layout apply` | `tc002 layout restore` |
| Start the background service (launchd, at login, restarted if it dies) | `tc002 service install` | `tc002 service uninstall` |
| Add Claude Code hooks to `~/.claude/settings.json` (existing hooks are kept; a backup is written first) | `tc002 hooks install` | `tc002 hooks uninstall` |

`tc002 uninstall` undoes all three. Run `tc002 install` again after changing the code
(`uv tool install --force .` first) or the config.

## Usage

```text
tc002 doctor                         check config, clock, firmware, service, hooks
tc002 text "BUILD OK" --color green  short text shimmers; long text scrolls, then clears
tc002 text "HELLO" --show            ...and switch the clock to it
tc002 alert "DEPLOYED" --kind done   chasing-lights alert, shown at once, removed after 10 s
tc002 alert "PROD DOWN" --kind error --keep
tc002 layout show                    built-in apps currently on, carousel setting
tc002 apps / tc002 rm [app...]       list / remove custom apps on the clock
tc002 info                           firmware, Wi-Fi, brightness
tc002 watch                          run screens + playlist in the foreground (Ctrl-C clears)
tc002 --preview out/ watch --once    write LED mock-up GIFs instead of touching the clock
tc002 service status                 is the background service running
```

Every command has `--help`. Colors: `white green yellow red blue orange cyan` or
`#RRGGBB`. Text is ASCII and shown upper case; other characters show as `?`.

From a script or CI step on the same network:

```bash
tc002 alert "TESTS GREEN" --kind done || true
```

## Configure

Edit [`tc002.toml`](tc002.toml) — every option is described in the file — then run
`tc002 install`. In short:

```toml
[screens]
enabled = ["claude", "sys"]

[device]
keep_builtins = ["clock"]          # every other built-in app is turned off

[playlist]
slots = [
  { screen = "claude", seconds = 30 },
  { screen = "sys", seconds = 15 },
  { builtin = "clock", seconds = 15 },
]

[alerts]
takeover = true                    # DONE / WAIT jump to the Claude screen at once
```

An empty `slots` list leaves the device's own carousel in charge.

## How it works

```text
tc002.toml ─► config ─► watcher ─┬─ screen threads ── sample → render → Output ─► POST /api/custom
                                 └─ playlist ─────── switchDiyApp / switchApp ──► clock
Claude Code hooks ─► tc002 event ─► ~/.cache/tc002/event.json ─► claude screen
```

See [docs/architecture.md](docs/architecture.md) for the module map and
[docs/decisions.md](docs/decisions.md) for why it is built this way.
[docs/device-notes.md](docs/device-notes.md) collects what the firmware actually does,
including the limits that shaped the animations.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Every request times out, but `curl http://<ip>/getBase` works | An `HTTP_PROXY` (e.g. Clash on `:7890`) — tc002 already bypasses it; if you call the clock from other tools, add the IP to `NO_PROXY`. |
| Log shows `No route to host` | macOS Local Network permission for the uv Python: System Settings → Privacy & Security → Local Network. |
| Screens never appear | The clock is not on the DIY page and no playlist is set — add slots, or press the knob to DIY. |
| `firmware ... update for switching` in `doctor` | Firmware older than V1.1.0 cannot switch screens remotely; update in Ulanzi Studio. |
| Clock unplugged | The service keeps retrying quietly and re-sends everything when it is back. |

Logs: `~/Library/Logs/tc002.log`.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_docs.py   # refresh docs/screens/*.gif
```

Commits and pull-request titles follow [Conventional Commits](https://www.conventionalcommits.org/);
releases, tags and `CHANGELOG.md` are produced by release-please — never edit the version
by hand.

## License

[MIT](LICENSE). Not affiliated with Ulanzi.
