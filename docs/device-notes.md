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

## Getting on Wi-Fi, and being found

- A clock with no usable network opens a WPA2 hotspot `U-Clock` (passphrase `12345678`,
  the same on every unit) and answers at `192.168.100.1`; requests get a captive-portal
  redirect first. `POST /setWifiConfig {"ssid", "password"}` makes it join a network. It
  replies `{"code":200, ...}` *before* trying, so a wrong password or a 5 GHz-only
  network shows only as the clock never appearing. 2.4 GHz only; no WPA3-only or
  enterprise networks. Sources: the official protocol file; community notes on a
  factory-fresh unit (github.com/atomicstack/tc002-customisation, facts only).
- On a network, every clock broadcasts `Ulanzi TC002 <mac tail>:<mac>:<serial>:<flag>`
  on UDP 55555 about once a second (seen from this repository's own clock on firmware
  1.1.3). tc002 listens for it first and sweeps the /24 only when nothing is heard.
- There is no mDNS name, no authentication, and no expiry for custom apps: an app stays
  on the clock until it is replaced or deleted with an empty body.
- macOS hides the current Wi-Fi name (`<redacted>`) from tools without Location
  permission, so the setup page asks for it instead of guessing.
