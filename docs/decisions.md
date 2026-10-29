# Decisions

## 2026-10-28 — Talk to the stock firmware over HTTP, not MQTT or custom firmware

- **Problem:** drive the clock from this Mac.
- **Options:** (a) HTTP API of the stock firmware; (b) MQTT through a broker; (c) flash
  custom firmware with Ulanzi's FlyThings SDK.
- **Evidence:** HTTP needs only the IP and answered every call in tests; MQTT carries the
  identical payload but adds a broker to run; custom firmware removes the HTTP/MQTT API
  and needs a Windows IDE and a TF card to flash.
- **Choice:** (a). MQTT remains possible later because the payloads are the same.

## 2026-10-28 — Render locally into one looping GIF per screen

- **Problem:** animated screens without a constant stream of requests.
- **Options:** (a) the firmware's `text`/`draw` primitives; (b) a full-screen `db` bitmap
  pushed per frame (~17 fps measured); (c) a locally rendered GIF the clock loops itself.
- **Evidence:** (a) has one fixed font and no animation; (b) works but costs one HTTP
  request per frame forever; (c) is accepted (`200`) and decoded correctly, and costs one
  request per state change.
- **Choice:** (c), with a stdlib GIF encoder and a local pixel font so terminal/LED
  previews match the device exactly. Limits (≤50 frames, ≤60 KB base64) are enforced in
  `Animation.payload()`; long marquees are cut into segments.

## 2026-10-28 — Hooks write a file; the service owns the clock

- **Problem:** show DONE/WAIT from Claude Code without slowing sessions.
- **Options:** (a) hook pushes an alert to the clock; (b) hook records an event the
  running service picks up.
- **Evidence:** (a) puts LAN latency and an offline clock on every turn and races the
  service for the screen; (b) measured 50 ms with no network.
- **Choice:** (b).

## 2026-10-29 — A tc002 playlist replaces the built-in carousel

- **Problem:** the custom screens should take the place of the preset apps, and alerts
  must be visible immediately.
- **Options:** (a) leave the device carousel on and only disable apps; (b) disable the
  unwanted apps and the device carousel, and let the service switch screens via
  `/api/switchDiyApp` and `/switchApp`.
- **Evidence:** pushing content never switches the display (protocol §3.1); only (b) can
  jump to an alert at once and mix custom screens with kept built-ins in one order.
- **Choice:** (b). The pre-change layout is saved once (flags and orders only, never
  tokens or passwords) so `tc002 uninstall` restores it.

## 2026-10-29 — Toolchain

Python 3.15 (latest stable), uv with the `uv_build` backend, ruff, pytest; no runtime
dependencies. CI and releases use the shared `Misoto22/ci` workflows pinned by SHA,
release-please for versions and changelog, Dependabot for `uv` and GitHub Actions.
