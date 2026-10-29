# tc002

Animated screens, a rotation that replaces the built-in carousel, and live Claude Code
status for the **Ulanzi TC002** pixel clock (52×16 RGB). Talks to the clock's stock
firmware over the LAN — no flashing, no cloud, no runtime dependencies beyond Python.

| Claude busy | Claude idle | DONE | WAIT |
|---|---|---|---|
| ![](docs/screens/claude-busy.gif) | ![](docs/screens/claude-idle.gif) | ![](docs/screens/claude-done.gif) | ![](docs/screens/claude-wait.gif) |

| AI usage | System | Text | Alert |
|---|---|---|---|
| ![](docs/screens/usage.gif) | ![](docs/screens/sys.gif) | ![](docs/screens/text.gif) | ![](docs/screens/alert-error.gif) |

## What it does

- **`claude` screen** — the spark spins while Claude Code is generating and breathes when
  idle; live sub-agents orbit it; then a card shows today's tokens. Claude Code hooks turn
  it into a green **DONE** when a turn ends and an orange **WAIT** when Claude needs you.
- **`usage` screen** — Claude Code and Codex token usage: today (counting up) and the last
  five hours, plus Codex's 5-hour and weekly allowance when Codex reports it. Read from
  each agent's local files; nothing leaves the machine.
- **`sys` screen** — scrolling CPU chart of the last 52 seconds plus memory.
- **Rotation** — cycles the clock between your screens and the built-in apps you keep, on
  your timing, replacing the device's own carousel; start from a preset (Coding focus,
  Developer desk, AI agents, Ambient, Just the clock). Built-in apps you did not keep are
  turned off, and restored by `tc002 uninstall`.
- **One-off messages** — `tc002 text` and `tc002 alert` from any script or CI job.

Every animation is rendered locally and sent as one looping GIF, so the clock animates by
itself and the screen is re-sent only when its content changes.

## Settings UI

```bash
tc002 ui            # opens http://127.0.0.1:8742
```

![Settings UI — rotation](docs/ui-rotation.png)

A local web app for everything tc002 manages, in English or Chinese, dark or light:

- **Device bar** — a live LED preview pinned above every page: the rotation cycling with
  real durations, or the built-in app you are editing, drawn with your draft settings
  (brightness included). One switch, **Live on the clock**, plays the draft on the
  hardware before saving (the rotation pauses); switching it off restores tc002.toml.
- **Quick settings** — brightness and volume from the top bar (and the overview), applied
  at once without touching unsaved edits.
- **Rotation** — presets, drag to reorder (or `Alt+↑/↓`), durations, screens and kept built-ins.
- **Built-in apps, Display, App settings** — which apps stay on; time zone, date and week;
  clock format, weather (search a city — it fills in coordinates), focus timers.
- **Status** — the top bar always says where things stand: in sync, *n* unsaved, saving,
  applied, saved-but-offline, failed, or live; click it for this session's activity.
- **⌘K** for anything, `⌘S` to save, `[` to collapse the sidebar.

![Settings UI — app settings](docs/ui-apps.png)

Every change goes to `tc002.toml` first, is applied to the clock, and reloads the
background service, so the file stays the single source of truth and a fresh clone
reproduces your setup. The server listens on 127.0.0.1 only, rejects foreign `Host`
headers and needs a per-session token for every change. Styling comes from one file of
design tokens (`web/static/css/tokens.css`); icons are monochrome — Lucide for the
interface and the apps' official marks (Simple Icons, plus a few from Iconify), vendored
by `scripts/vendor_icons.py`.

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
| Keep only the built-in apps in `device.keep_builtins`; turn off the device carousel when a rotation is set | `tc002 layout apply` | `tc002 layout restore` |
| Start the background service (launchd, at login, restarted if it dies) | `tc002 service install` | `tc002 service uninstall` |
| Add Claude Code hooks to `~/.claude/settings.json` (existing hooks are kept; a backup is written first) | `tc002 hooks install` | `tc002 hooks uninstall` |

`tc002 uninstall` undoes all three. Run `tc002 install` again after changing the code
(`uv tool install --force .` first) or the config.

## Usage

```text
tc002 ui                             settings UI in the browser (local only)
tc002 doctor                         check config, clock, firmware, service, hooks
tc002 text "BUILD OK" --color green  short text shimmers; long text scrolls, then clears
tc002 text "HELLO" --show            ...and switch the clock to it
tc002 alert "DEPLOYED" --kind done   chasing-lights alert, shown at once, removed after 10 s
tc002 alert "PROD DOWN" --kind error --keep
tc002 layout show                    built-in apps currently on, carousel setting
tc002 apps / tc002 rm [app...]       list / remove custom apps on the clock
tc002 info                           firmware, Wi-Fi, brightness
tc002 watch                          run screens + rotation in the foreground (Ctrl-C clears)
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

Use `tc002 ui`, or edit [`tc002.toml`](tc002.toml) — every option is described in the file —
and run `tc002 layout apply`. In short:

```toml
[screens]
enabled = ["claude", "sys"]

[device]
keep_builtins = ["clock"]          # every other built-in app is turned off

[display]                          # optional: clock-wide settings
volume = 2
timezone = "UTC+10"
brightness = { level = "mid" }

[apps.weather]                     # optional: built-in app settings (never credentials)
city = "Sydney"

[rotation]
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
                                 └─ rotation ─────── switchDiyApp / switchApp ──► clock
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
| Screens never appear | The clock is not on the DIY page and no rotation is set — add slots, or press the knob to DIY. |
| `firmware ... update for switching` in `doctor` | Firmware older than V1.1.0 cannot switch screens remotely; update in Ulanzi Studio. |
| Clock unplugged | The service keeps retrying quietly and re-sends everything when it is back. |

Logs: `~/Library/Logs/tc002.log`.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_docs.py   # refresh docs/screens/*.gif
uv run python scripts/vendor_icons.py  # refresh the icon sprite and app-icons.json
```

Commits and pull-request titles follow [Conventional Commits](https://www.conventionalcommits.org/);
releases, tags and `CHANGELOG.md` are produced by release-please — never edit the version
by hand.

## License

[MIT](LICENSE). Not affiliated with Ulanzi.
