# Architecture

`src/tc002/` is layered so that each layer only imports the ones below it.

```text
cli/            parser.py (commands, help)  ·  commands.py (handlers)  ·  __init__ (dispatch, errors)
web/            server.py (HTTP, host/token guard)  ·  api.py (state, save, actions)  ·  static/ (UI)
  │
integrations/   launchd.py (background service)  ·  claude_hooks.py (~/.claude/settings.json)
runtime/        watcher.py (threads, signals)  ·  playlist.py (what is on screen)
                output.py (push or preview, change detection)  ·  events.py (hook → file)
  │
screens/        claude.py  ·  sysmon.py  ·  message.py (text, alerts)
  │
render/         canvas.py (52×16 buffer)  ·  font.py  ·  anim.py (frames + limits)
                gif.py (encoder)  ·  mockup.py (LED previews)
  │
sync.py (tc002.toml → clock, restore)  ·  config_writer.py (tc002.toml writer)
config.py (tc002.toml + local state)  ·  device_settings.py (allowed values)
builtins.py (built-in app catalogue)  ·  device.py (HTTP client)
```

| Module | Owns |
|---|---|
| `device.py` | Every HTTP call to the clock, proxy bypass, retry, error mapping |
| `builtins.py` | Built-in app names → category/index, enabling/disabling them, the saved original layout |
| `config.py` | Parsing and validating `tc002.toml`; machine-local state in `~/.config/tc002/local.json` |
| `config_writer.py` | Writing `tc002.toml` back in a canonical, commented form (stdlib cannot write TOML) |
| `device_settings.py` | The allowed values of every `[display]` and `[apps.*]` setting; validates the file and describes the UI's controls |
| `sync.py` | The only code that pushes `tc002.toml` to the clock; saves and restores the original layout |
| `web/` | `tc002 ui`: a stdlib HTTP server bound to 127.0.0.1 and a no-build ES-module front end |
| `render/` | Pixels only: no I/O except writing bytes |
| `screens/` | One class per live screen: `APP`, `TICK`, `sample() → state`, `render(state) → Animation` |
| `runtime/output.py` | Sending an `Animation`; skips unchanged ones; logs an outage once |
| `runtime/playlist.py` | Choosing what the clock displays; alerts pre-empt the playlist |
| `runtime/watcher.py` | One thread per screen + the playlist; SIGTERM/Ctrl-C remove the screens |
| `runtime/events.py` | The only contract between Claude Code hooks and the running service |
| `integrations/` | Everything that edits the host: launchd plist, Claude settings |

## Data flow

1. A screen thread calls `sample()` every `TICK` seconds (`claude`: 2 s, `sys`: ~1.2 s).
2. `render(state)` returns an `Animation` whose `key` is the state. `Output` sends it only
   when the key changed or 60 s passed (so a rebooted clock gets its screens back).
3. If the state carries an `alert`, the screen marks itself in `Attention`; the playlist
   switches to it at once and resumes the rotation when the alert clears.
4. Hooks never talk to the clock: `tc002 event done|wait|clear` writes one small JSON file
   in about 50 ms, which the `claude` screen reads on its next sample.

## Adding a screen

1. Create `screens/<name>.py` with a class exposing `APP`, `TICK`, `sample()` and
   `render(state) -> Animation` (keep a GIF within 50 frames; `Animation.payload()` checks).
2. Register it in `screens/__init__.py` (`SCREENS`).
3. Enable it in `tc002.toml` and optionally give it a playlist slot.
4. Add tests next to the others and an example to `scripts/render_docs.py`.

## State on disk

| Path | Content |
|---|---|
| `~/.config/tc002/local.json` | Clock IP and the path of your `tc002.toml` |
| `~/.config/tc002/original-layout.json` | Built-in app enable flags, orders and carousel before tc002 changed them — **no tokens or passwords** |
| `~/.cache/tc002/event.json` | Last Claude Code hook event |
| `~/Library/LaunchAgents/dev.tc002.watch.plist` | Background service |
| `~/Library/Logs/tc002.log` | Service log |
| `~/.claude/settings.json.bak-tc002` | Backup taken before the first hook install |

## Web UI

`tc002 ui` serves `web/static/` and a JSON API from one `ThreadingHTTPServer` on
127.0.0.1. The page is plain ES modules — `app.js` (state, routing, save bar),
`views.js` (one function per page), `ui.js` (element helper and controls),
`sortable.js` (pointer/keyboard reordering with FLIP animation) — and one stylesheet of
design tokens, so there is no Node toolchain to install and nothing to build.

| Endpoint | Does |
|---|---|
| `GET /api/state` | tc002.toml, the clock's live settings (credentials reported only as present), drift between the two, service and hook status, and the control schema |
| `POST /api/config` | Validate a full tc002.toml document, write it, `sync.apply` it, restart the service |
| `POST /api/show` | Switch the clock to a screen or built-in app now |
| `POST /api/message` | Play a text or alert, then clear it |
| `GET /api/preview/<name>.gif` | LED mock-up of an example screen or a message draft |

Errors are RFC 9457 `application/problem+json`. Requests must name this server in `Host`
(DNS-rebinding guard); writes must send the token embedded in the page (cross-site guard);
the page's CSP allows only same-origin scripts and styles.
