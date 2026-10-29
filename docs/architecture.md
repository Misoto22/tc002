# Architecture

`src/tc002/` is layered so that each layer only imports the ones below it.

```text
cli/            parser.py (commands, help)  ·  commands.py (handlers)  ·  __init__ (dispatch, errors)
web/            server.py (HTTP, host/token guard)  ·  api.py (state, save, actions)  ·  static/ (UI)
  │
integrations/   launchd.py (background service)  ·  claude_hooks.py, statusline.py (~/.claude/settings.json)
runtime/        watcher.py (threads, signals)  ·  rotation.py (what is on screen)
                output.py (push or preview, change detection)  ·  sessions.py (hook → per-session file)
  │
screens/        claude.py  ·  sysmon.py  ·  message.py (text, alerts)
  │
render/         canvas.py (52×16 buffer)  ·  font.py  ·  palette.py (LED colours)  ·  anim.py
                gif.py (encoder)  ·  mockup.py (LED previews)
  │
sync.py (tc002.toml → clock, restore)  ·  config_writer.py (tc002.toml writer)  ·  presets.py
usage/ (Claude Code and Codex token counts and plan limits from local files)
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
| `runtime/rotation.py` | Choosing what the clock displays; alerts pre-empt the rotation |
| `runtime/watcher.py` | One thread per screen + the rotation; SIGTERM/Ctrl-C remove the screens |
| `runtime/sessions.py` | The only contract between Claude Code hooks and the service and UI: one state file per session |
| `usage/limits.py` | Claude Code's 5-hour and 7-day % used, as its status line reports them |
| `integrations/` | Everything that edits the host: launchd plist, Claude hooks, the status line wrapper |

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

| Endpoint | Does |
|---|---|
| `GET /api/state` | tc002.toml, the clock's live settings (credentials reported only as present), drift, service and hook status, control schema |
| `GET /api/led` | Pixel fonts and LED palette, so browser previews match pushed frames |
| `POST /api/quick` · `/api/preset` | Apply display settings at once · a draft with a preset's rotation |
| `GET /api/cities?q=&lang=` | City search: built-in prefix matches plus Open-Meteo geocoding |
| `GET /api/preview/<name>.gif` | LED mock-up of an example screen or a message draft |
| `POST /api/config` | Validate a full tc002.toml document, write it, `sync.apply` it, restart the service |
| `POST /api/live` · `/api/live/stop` | Apply a draft without saving and hold the rotation (`runtime/hold.py`, ≤5 min) · put tc002.toml back and release |
| `POST /api/show` · `/api/message` | Switch the clock now · play a text or alert, then clear it |

Errors are RFC 9457 `application/problem+json`. Requests must name this server in `Host`
(DNS-rebinding guard); writes must send the token embedded in the page (cross-site guard);
the page's CSP allows only same-origin scripts and styles.
