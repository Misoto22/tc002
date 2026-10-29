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

## 2026-10-29 — tc002.toml owns display and built-in app settings too

- **Problem:** a settings UI needs somewhere to keep brightness, volume, weather city, ….
- **Options:** (a) the UI writes straight to the clock; (b) the UI writes tc002.toml and
  `sync.apply` pushes it.
- **Evidence:** (a) leaves the repository unable to reproduce the setup and makes two
  owners of the same values; (b) keeps one owner and lets `tc002 install` rebuild
  everything on a new machine or clock. Credentials stay out: the API reports only that
  an account is linked.
- **Choice:** (b). The UI shows where the clock has drifted from the file.

## 2026-10-29 — Settings UI without a front-end build

- **Problem:** a Linear-style settings app that drags, previews and saves, served by the
  CLI and usable straight after `git clone`.
- **Options:** (a) React 19 + Vite + TypeScript, built output shipped in the package;
  (b) standard ES modules and modern CSS served as-is.
- **Evidence:** (a) needs Node in every clone and committed build output with a drift
  check; (b) covers the whole UI (seven pages, drag-and-drop, live GIF previews) in about
  1,100 lines with zero dependencies and works offline. Verified in Chrome in dark and
  light mode, against the real clock.
- **Choice:** (b), on the current web platform (ES modules, `structuredClone`, CSS custom
  properties, `prefers-color-scheme`, Web Animations). Revisit if the UI outgrows it.

## 2026-10-29 — Live preview holds the playlist through a file

- **Problem:** "preview on the hardware" must show a draft on the clock without the
  background playlist switching it away, and must never strand the clock in a draft.
- **Options:** (a) the UI stops the service while previewing; (b) a short-lived hold file
  the playlist checks each step.
- **Evidence:** (a) also stops the Claude/CPU screens and needs launchd access from the
  UI; (b) is one small file, expires on its own (≤5 min, renewed every minute while
  live), and the page restores tc002.toml on exit.
- **Choice:** (b), `runtime/hold.py`. Verified on the clock: timeFormat went to
  `HH:MM:SS` while live and back to `HH:MM` on stop.

## 2026-10-29 — Icons from Lucide, vendored as a sprite

Lucide (ISC) is the icon set closest to Linear's; `scripts/vendor_icons.py` pulls the
icons the UI uses from a pinned `lucide-static` release into `web/static/icons.svg`, so
the UI works offline and the sprite changes only through the script.
