# Device notes

What the TC002 stock firmware does in practice. The authoritative API reference is
Ulanzi's [protocol document](https://github.com/UlanziTechnology/Ulanzi-U-Clock-TC002/tree/main/protocol);
this page records what tc002 relies on and what was measured.

## Endpoints used

| Purpose | Call | Module |
|---|---|---|
| Push / delete a screen | `POST /api/custom?name=<app>` (body `{}` deletes) | `device.push`, `device.remove` |
| List screens | `GET /api/customList` | `device.apps` |
| Show a screen | `POST /api/switchDiyApp?name=<app>` (firmware V1.1.0+) | `device.switch_custom` |
| Show a built-in app | `POST /switchApp` `{"type","index"}` | `device.switch_builtin` |
| Built-in app configs | `GET/POST /getToolsConfig`, `/getSocial`, `/getCalendar` and their `set` pairs | `builtins` |
| Global settings | `GET /getConfig`, `POST /setConfig` (merge) | `device.config`, `device.set_config` |
| Device info | `GET /getBase` | `device.info` |

## Limits that shaped the design

- GIF image element: ≤256×256, **≤50 frames**, **≤60 KB** after base64; up to 3 GIFs per app.
- Draw commands: ≤32 per app; `db` bitmaps are row-major `0x00RRGGBB` ints.
- Built-in text: ASCII only, font height 5 or 10, no scrolling.
- `xxxOrder` arrays must list every index of the category or the call returns 400.
- Pushing content does not change what is displayed.

## Measured behaviour

| Observation | Consequence |
|---|---|
| HTTP replies have no `Content-Length` and close the connection | Fine for `urllib`; a mock server in the tests does the same |
| Python's `urllib` honours `HTTP_PROXY`; a local proxy cannot reach the LAN and requests hang | `device.py` builds an opener with an empty `ProxyHandler` |
| The first request after a quiet period sometimes times out | One automatic retry |
| Full-screen `db` pushes sustain about 17 per second | Viable fallback for real-time effects |
| A 24-frame GIF pushed once animates on the device | Basis of every screen |
| A launchd agent's first requests can fail with `No route to host` until macOS grants Local Network access | Documented under Troubleshooting |
