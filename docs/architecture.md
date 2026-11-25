# Architecture

`src/tc002/` is a stack of units. Each unit may import only the units its row names
below; nothing imports upward or sideways, and only the standard library is used. This
table is generated from `LAYERS` in `tests/test_architecture.py`, which checks every
import in the code against it (and this copy against `LAYERS`), so the table is the
architecture rather than a picture of it.

<!-- layers:start -->
| Unit | Owns | May import |
|---|---|---|
| `cli/` | `tc002` commands: parse, call App, print; starts the web and MCP servers | `app`, `web.server`, `mcp.server` |
| `web/` | `tc002 ui`: HTTP transport, request shapes, static front end | `app` |
| `mcp/` | `tc002 mcp`: JSON-RPC over stdio, tool schemas | `app` |
| `app/` | Every use case, as App methods; typed errors; the catalogue front ends show | `config`, `runtime`, `screens`, `games`, `lookup`, `host`, `clock`, `state`, `usage`, `render`, `paths`, `net` |
| `config/` | tc002.toml: parse, validate, write; presets | `runtime`, `screens`, `host`, `clock`, `render`, `paths` |
| `runtime/` | Loops that drive the clock: service, rotation, output, night, game session | `screens`, `games`, `clock`, `state`, `render`, `paths` |
| `screens/` | Live screens: sample() -> state, render(state) -> Animation | `host`, `clock`, `state`, `usage`, `render`, `net`, `paths` |
| `games/` | Game rules and drawing, no I/O | `render` |
| `lookup/` | Searches for the UI's pickers: cities, stock symbols | `net` |
| `host/` | This Mac: launchd, Claude Code hooks and status line, Keychain, Finder | `usage`, `paths` |
| `clock/` | The TC002: HTTP client, built-in apps, settings rules, sync, Wi-Fi, discovery | — |
| `state/` | Small state files shared by service, UI and hooks | `paths` |
| `usage/` | Claude Code and Codex usage read from local files | `paths` |
| `render/` | Pixels only: canvas, fonts, palette, GIF | — |
| `paths/` | Where tc002 keeps files | — |
| `net/` | Outgoing HTTP for screens and lookups | — |
<!-- layers:end -->

Rules the same test enforces:

- **Front ends call only `app`.** `cli/`, `web/` and `mcp/` turn their input into one
  `App` call and its result into their output. They import `app` (and `app.catalog` for
  names and allowed values, `app.errors` for errors) and do no I/O of their own beyond
  their transport: no `subprocess`, sockets or outgoing HTTP.
- **`App` raises only `app.errors`.** `app/base.py` (`guarded`) turns a `DeviceError`,
  `ConfigError`, `ProvisionError` or failing command into `ClockUnreachable`,
  `InvalidSettings`, `InvalidRequest` or `CommandFailed`, so front ends map one family
  of errors (`web/errors.py`: to HTTP statuses; `mcp/server.py`: to tool errors; `cli/`:
  to exit codes).
- **Every module is in exactly one unit, and there are no import cycles.** A new
  package or top-level module fails the build until it is given a place in `LAYERS`.

CI runs the test on every pull request. Claude Code also runs it when it ends a turn in
this repository (a Stop hook: `.claude/settings.json` → `.claude/hooks/check-architecture.sh`)
and is handed the violations to fix before it stops; one that it cannot fix is shown to
you instead of looping.

## Modules

```text
cli/        __init__ (dispatch, exit codes) · parser.py (arguments) · commands.py (print App results)
web/        server.py (HTTP, Host/token guard) · api.py (path → App call) · errors.py · static/ (UI)
mcp/        server.py (JSON-RPC 2.0 over stdio) · tools.py (tools, JSON Schemas, hints)
app/        App = Reads + OnScreen + Configure + Host + Setup + Content (see app/__init__.py)
            base.py (clock, tc002.toml, guarded) · errors.py · catalog.py · clock_report.py · agents.py
config/     __init__ (parse, validate, local.json) · writer.py (canonical TOML) · presets.py
runtime/    watcher.py (the service) · rotation.py · output.py · freshness.py · night.py · game.py
screens/    one module per live screen · message.py · examples.py · builtin_previews.py · options.py
games/      breakout, pong, snake · frame.py (a frame, game over included) · demo.py
lookup/     cities.py (built-in list + Open-Meteo) · symbols.py (Yahoo Finance search)
host/       launchd.py · claude_hooks.py · statusline.py · keychain.py · connections.py · finder.py
clock/      device.py (HTTP client) · builtins.py · device_settings.py · sync.py · tz.py
            provision.py (Wi-Fi) · discovery.py (find a clock on the LAN)
state/      sessions.py (one file per Claude Code session) · focus.py · hold.py
usage/      claude.py · codex.py · limits.py · claude_login.py
render/     canvas.py (52×16) · font.py · palette.py · anim.py · gif.py · mockup.py · themes.py
paths.py · net.py
```

| Module | Owns |
|---|---|
| `app/base.py` | Which clock and tc002.toml an `App` acts on, the clock client, settings as on disk now, and `guarded` |
| `app/catalog.py` | Names, allowed values and limits the front ends show (screens, built-ins, colours, display rules, games) |
| `app/settings.py` | The one "save" path: validate → write tc002.toml under one lock, never over a newer file → `sync.apply` → restart the service |
| `clock/device.py` | Every HTTP call to the clock, proxy bypass, retry, error mapping |
| `clock/builtins.py` | Built-in app names → category/index, enabling/disabling them, the saved original layout |
| `clock/device_settings.py` | The allowed values of every `[display]` and `[apps.*]` setting; validates the file and describes the UI's controls |
| `clock/sync.py` | The only code that pushes `tc002.toml` to the clock; saves and restores the original layout |
| `clock/tz.py` | The clock following this Mac's time zone: the zone's POSIX rule (from /etc/localtime) sent as `timezoneEx`, and `Follow`, which the service runs to send it again when the Mac moves |
| `config/` | Parsing and validating `tc002.toml`; machine-local state in `~/.config/tc002/local.json`; writing it back in a canonical, commented form (stdlib cannot write TOML) |
| `runtime/night.py` | The screen fully dark: the `[night]` schedule, "screen off/on now", the black `night` app, and `Watch`, which pauses the service while it is dark |
| `runtime/output.py` | Sending an `Animation`; skips unchanged ones; logs an outage once |
| `runtime/rotation.py` | Choosing what the clock displays; alerts pre-empt the rotation |
| `runtime/watcher.py` | One thread per screen + the rotation; SIGTERM/Ctrl-C remove the screens |
| `state/sessions.py` | The only contract between Claude Code hooks and the service and UI: one state file per session |
| `screens/` | One class per live screen: `APP`, `TICK`, `sample() → state`, `render(state) → Animation` |
| `render/` | Pixels only: no I/O except writing bytes |
| `usage/limits.py` | Claude Code's 5-hour and 7-day % used, as its status line reports them |
| `host/` | Everything that edits or asks this Mac: launchd plist, Claude hooks, the status line wrapper, Keychain, Finder |

Naming: `screens/<name>.py` is the screen called `<name>` in tc002.toml, and reads its
data from the unit below that owns it (`screens/usage.py` from `usage/`,
`screens/focus.py` from `state/focus.py`, `screens/claude.py` from `state/sessions.py`).

## Data flow

1. A screen thread calls `sample()` every `TICK` seconds (`claude`: 2 s, `sys`: ~1.2 s).
2. `render(state)` returns an `Animation` whose `key` is the state. `Output` sends it only
   when the key changed or 60 s passed (so a rebooted clock gets its screens back).
3. If the state carries an `alert`, the screen marks itself in `Attention`; the rotation
   switches to it at once and resumes the rotation when the alert clears.
4. Hooks never talk to the clock: `tc002 hook` reads the hook's JSON from stdin and writes
   one small file per session, which the `claude` screen and the UI read. Claude Code's
   status line runs `tc002 statusline`, which saves the plan limits and then runs the
   status line command you had before, printing its output unchanged.

## Adding a screen

1. Create `screens/<name>.py` with a class exposing `APP`, `TICK`, `sample()` and
   `render(state) -> Animation` (keep a GIF within 50 frames; `Animation.payload()` checks).
2. Register it in `screens/__init__.py` (`SCREENS`).
3. Enable it in `tc002.toml` and optionally give it a rotation slot.
4. Add tests next to the others and an example to `scripts/render_docs.py`.

## State on disk

| Path | Content |
|---|---|
| `~/.config/tc002/local.json` | Clock IP and the path of your `tc002.toml` |
| `~/.config/tc002/original-layout.json` | Built-in app enable flags, orders and carousel before tc002 changed them — **no tokens or passwords** |
| `~/.cache/tc002/sessions/*.json` | Each Claude Code session's state (working, waiting, done, idle) |
| `~/.cache/tc002/night.json` | "Screen off now" / "kept on tonight", with when it ends |
| `~/.cache/tc002/claude-limits.json` | Last 5-hour and 7-day % from the status line |
| `~/.config/tc002/statusline.json` | Your previous status line command, restored on uninstall |
| `~/Library/LaunchAgents/dev.tc002.watch.plist` | Background service |
| `~/Library/Logs/tc002.log` | Service log |
| `~/.claude/settings.json.bak-tc002` | Backup taken before the first hook install |

## Web UI

`tc002 ui` serves `web/static/` and a JSON API from one `ThreadingHTTPServer` on
127.0.0.1. The front end is plain ES modules — no build step, no Node:

| File | Owns |
|---|---|
| `js/app.js` | Shell: sidebar, top bar, save bar, routing, shortcuts |
| `js/store.js` | State, the tc002.toml draft and its diff, save/apply status, activity log, live preview |
| `js/i18n.js` · `js/prefs.js` | English/Chinese strings · theme, language and sidebar preferences |
| `js/assets.js` · `js/media.js` · `js/quick.js` | App icons and LED data loaded once · which preview a screen uses · quick settings |
| `js/preview.js` · `js/led.js` · `js/sims.js` | Preview panel · 52×16 LED canvas using the server's pixel fonts · approximations of the built-in apps |
| `js/palette.js` · `js/citypicker.js` · `js/sortable.js` · `js/ui.js` | ⌘K palette · city combobox · drag reorder · element helper, controls, Lucide icons |
| `js/pages/*.js` | One module per page |
| `css/tokens.css` · `base.css` · `components.css` · `motion.css` | Design tokens (dark/light) · layout and controls · components · animation |
| `icons.svg` · `app-icons.json` | Lucide + official app marks, and which mark each app uses; both generated by `scripts/vendor_icons.py` |

Every endpoint is one line in `web/api.py` (`GETS`, `POSTS`): a path, the App method it
calls, and how the request maps onto its arguments.

| Endpoint | Does |
|---|---|
| `GET /api/state` | tc002.toml, the clock's live settings (credentials reported only as present), drift, service and hook status, control schema |
| `GET /api/led` | Pixel fonts and LED palette, so browser previews match pushed frames |
| `POST /api/quick` · `/api/preset` | Apply display settings at once · a draft with a preset's rotation |
| `GET /api/cities?q=&lang=` | City search: built-in prefix matches plus Open-Meteo geocoding |
| `GET /api/preview/<name>.gif` | LED mock-up of an example screen or a message draft |
| `POST /api/config` | Validate a full tc002.toml document, write it, `sync.apply` it, restart the service |
| `POST /api/live` · `/api/live/stop` | Apply a draft without saving and hold the rotation (`state/hold.py`, ≤5 min) · put tc002.toml back and release |
| `POST /api/night` | Screen off now (`{"off": true, "until": "morning" \| null}`) or back on |
| `POST /api/show` · `/api/message` | Switch the clock now · play a text or alert, then clear it |

Application errors map to HTTP in `web/errors.py`: `NotConfigured` and `Conflict` → 409,
`NotFound` → 404, `InvalidRequest`/`InvalidSettings` → 422, `ServiceUnavailable` → 502,
`CommandFailed` → 500, `ClockUnreachable` → 502 (404 when the clock has no such app).
Errors are RFC 9457 `application/problem+json`. Requests must name this server in `Host`
(DNS-rebinding guard); writes must send the token embedded in the page (cross-site guard);
the page's CSP allows only same-origin scripts and styles.

## MCP server

`tc002 mcp` reads one JSON-RPC 2.0 message per line on stdin and writes each reply as one
line on stdout (the MCP stdio transport), with no SDK: `initialize`, `ping`, `tools/list`,
`tools/call`, `resources/list`, `resources/read`. While it runs, `sys.stdout` points at
stderr, so nothing but protocol messages reaches the client. Tool arguments are checked
against each tool's JSON Schema before the `App` method runs; an `AppError` comes back as a
tool result with `isError: true` and its title and detail, so the model can correct itself.
`send_message` returns at once and plays in the background, like the UI.
