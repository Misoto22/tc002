# Architecture

`src/tc002/` is layered so that each layer only imports the ones below it.

```text
cli/            parser.py (commands, help)  ·  commands.py (handlers)  ·  __init__ (dispatch, errors)
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
config.py (tc002.toml + local state)  ·  builtins.py (built-in app catalogue)  ·  device.py (HTTP client)
```

| Module | Owns |
|---|---|
| `device.py` | Every HTTP call to the clock, proxy bypass, retry, error mapping |
| `builtins.py` | Built-in app names → category/index, enabling/disabling them, the saved original layout |
| `config.py` | Parsing and validating `tc002.toml`; machine-local state in `~/.config/tc002/local.json` |
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
