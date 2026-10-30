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

## 2026-10-29 — "Rotation", not "playlist"

A playlist plays through and stops; the clock cycles forever. The UI, the code and
tc002.toml now say **rotation** (`[rotation]`); `[playlist]` is still read, and a file
with both is rejected so the two cannot disagree.

## 2026-10-29 — Agent token usage from local files only

- **Claude Code:** `message.usage` in `~/.claude/projects/**/*.jsonl`, de-duplicated by
  (message id, request id) as ccusage does; read incrementally (first scan ~3.4 s, then
  ~0.7 s on this machine). Totals include cache reads and writes.
- **Codex:** rollout `token_count` events (tokens and 5-hour / weekly allowance) when
  present; otherwise `threads.tokens_used` from the newest `state_*.sqlite`, opened
  read-only. This machine has no rollout files, so the allowance path is covered by tests
  only.
- No account APIs: nothing leaves the machine, and nothing needs credentials.

## 2026-10-29 — Monochrome icons, official marks, tokens everywhere

Interface icons are Lucide; built-in apps use their official marks (Simple Icons, and
Iconify for Lark, DingTalk, WeCom, Outlook and OpenAI), all drawn in the text colour on a
neutral tile — brand-coloured tiles were tried and dropped as out of keeping with the
quiet UI. Every colour, radius, size and duration lives in `tokens.css`; the LED palette
lives in `render/palette.py` and reaches the browser through `/api/led`.

## 2026-10-29 — Device bar instead of a third column

The preview moved from a right-hand column into a sticky bar above the page, and the
sidebar collapses to an icon rail (`[`): two columns read better than three, and the
preview stays in view without squeezing the settings.

## 2026-10-29 — Sessions and plan limits on the clock; paper-and-ink UI

**Problem.** The clock showed token counts, which say little (98.7 % of today's 218.7M
Claude Code tokens on this Mac were cache reads). It could not say how many sessions
were running, which were waiting for you, or how much of the plan allowance was left.
The web UI read as a dashboard of the conversation that built it rather than a product.

**Options.**
1. Keep token counts, add more pages to the web UI.
2. Show plan limits and per-session states on the clock; the web UI explains and
   configures rather than duplicates.

**Evidence.** Claude Code passes `rate_limits.five_hour` / `seven_day` (`used_percentage`,
`resets_at`) to the status line command; Codex writes `rate_limits` into its session logs.
Hooks receive `session_id`, `cwd`, `transcript_path` on stdin. Mock-ups of every screen at
52 × 16, rendered with tc002's own fonts, and of the UI:
https://claude.ai/artifact/KW24XneQgms3KrSWmJaaYA

**Choice.** Option 2. One row per agent on the `usage` screen; RUN / ASK / OK columns on
the `claude` screen with a takeover while a session waits. Hooks write one file per
session (no shared-file races); `tc002 statusline` wraps the user's status line and keeps
the previous command in its own file instead of re-quoting it. The UI moves to a light
paper, ink and single vermilion accent style with a modern sans (Inter Tight).

## 2026-10-29 — From a personal setup to a manager for every TC002

**Problem.** tc002 grew around one person's desk: Claude Code screens first, the clock's
own settings second, a tracked personal `tc002.toml`, one fixed LED palette, setup that
assumed the clock was already on Wi-Fi, and no way to add data from other services.

**Evidence.** A new TC002 opens a `U-Clock` hotspot (WPA2 `12345678`, clock at
`192.168.100.1`) and accepts `POST /setWifiConfig {ssid, password}` (official protocol
file; community reports on a factory unit). Joined clocks broadcast on UDP 55555. The
`draw` command takes a full-frame `db` bitmap; about 8 frames/s over HTTP is reported to
work, enough for simple games driven from the Mac's keyboard. Open-Meteo, Coinbase, Hacker
News and the `gh` CLI need no key; Home Assistant, YouTube and private calendar URLs do.

**Choices** (owner's answers, recorded in order of delivery):
1. LED palettes for tc002's own screens (the firmware's apps cannot be recoloured), chosen
   in Display & sound or set to follow the UI's colour theme.
2. Setup from a factory-fresh clock: hotspot → Wi-Fi details sent to the clock (never
   stored) → discovery by broadcast → firmware check → time zone and city → layout.
3. More screens that need no API: Pomodoro, countdown, world clock, sunrise/sunset, moon
   phase, day/week/year progress, Game of Life, ambient fire and sand.
4. Keyboard mini-games (Breakout, Snake, Pong) streamed as `draw` frames; written from
   scratch, taking ideas only from permissively licensed projects.
5. API screens with a Connections page; keys and private URLs live in the macOS Keychain
   (an `op://` reference is also accepted), never in `tc002.toml`.
6. Public repository and a PyPI release, so `uvx tc002 ui` works for anyone.

## 2026-10-29 — See everything before turning it on

**Problem.** The UI was split into pieces a new owner could not connect: presets, the
slot list and what the clock was showing were three separate ideas; screens, alert
takeover and the focus timer were switches with no picture; built-in apps were turned on
in one page and set up in another, so social apps looked like bare switches; the games
were icons; the quick settings' sun read as the light/dark switch; Safari showed a globe
for the tab icon; the README gallery's rows did not line up; a city search for 上海
listed five villages of that name.

**Evidence.** The firmware can only show one app at a time, so "rotate" and "show one"
are the two things the clock can do with tc002's screens. Safari ignores SVG favicons and
every browser asks for `/favicon.ico`. GitHub sizes a Markdown table's columns by their
header text, so images of one aspect ratio still render at different heights. Open-Meteo
returns a GeoNames feature code and population for each place: the city of Shanghai is
`PPLA` with 24.9 M people; the villages are `PPL` with no population.

**Choices.**
1. One page, *On the clock*: choose **Rotate** or **Show one** (`[rotation] mode`,
   `show`), then the list or a grid of pictures to pick from; templates below; then every
   tc002 screen with its picture, a line on what it shows, its switch and its options;
   then alert takeover beside an example of the alert. Rejected: keeping presets on their
   own (they only ever replace the list).
2. *Built-in apps* absorbs *App settings*: each app has its picture, its switch and its
   settings under it, social account IDs and tokens included.
3. Session counts and plan limits are shown on the clock only; the Sessions page and the
   overview's limit cards are gone. The overview shows what the clock is showing, as
   pictures, and the focus timer with its screen.
4. Games preview themselves: an autopilot plays each for 6 s (`games/demo.py`).
5. Setup leaves the sidebar; it opens on first run and from the overview's clock row.
   Brightness & volume moves to the foot of the sidebar with its name beside the icon.
6. Icons drop their tiles; Claude Code and Codex marks keep their own colours. Groups are
   cards; a rule only separates rows inside a card (the page-head rule and the cycle bar
   are gone).
7. Favicons: PNG and ICO rasterised from `favicon.svg` by a script, checked by a test.
8. City search lists capitals and provincial capitals always, other towns from 15,000
   people, largest first; never neighbourhoods or islands; the largest few small towns
   only when nothing else matches.
9. README: a light/dark hero drawn from the UI tokens and the clock's own pixel font, and
   the gallery as an HTML table with one image width.

## 2026-10-29 — Each item gets its own page

**Problem.** Every setting sat on one long page: a stock was one text box for a ticker,
Moon and Game of Life had no settings, switching a screen on did not say where it would
show, a connection test answered only "works", social apps were drawn as initials, and
switching pages took a moment.

**Evidence.** Hacker News's Firebase API lists ranked ids and reads each item separately
(no rate limit; about 2 s a request from this network), so reading stories in batches
and stopping once enough pass keeps a test near 6 s instead of 12 s. Desk displays for
Home Assistant (Tidbyt `hassentitylist`, AWTRIX blueprints) show one entity per page with
units and words for binary states, from one `GET /api/states`. Yahoo Finance's search
endpoint finds tickers by company name without a key (`tencent` → `0700.HK`). The page
delay was a 240 ms cross-fade plus staggered entrances, and each preview GIF was drawn
again on every request (about 0.4 s each).

**Choices.**
1. `#rotation/<screen>` and `#builtins/<app>` pages with a breadcrumb (also in the top
   bar): the picture read with real data and the options not yet saved, what was read and
   how long it took, where it shows, and every option.
2. "Where it shows" has four answers everywhere — off, kept without a turn, in the
   rotation (for how long), shown alone — as a menu on each list row and a control on the
   item's page; switching to one moves the item in the rotation list itself.
3. Several items per screen through one pager (`screens/pager.py`): fetched together every
   `refresh` minutes, shown one at a time, so each GIF stays within the frame limit.
   Stocks: up to four, found by search. Hacker News: list, how many, minimum points,
   keyword. Home Assistant: up to six entities, picked from the user's own server.
4. Moon: hemisphere, and % lit or days to full. Game of Life: speed, density, colour,
   how often to start again.
5. Testing a connection or the clock shows the result in place, not a toast.
6. Social apps' previews draw each service's mark as pixel art.
7. Pages draw at once with a 120 ms fade; fixed previews are drawn once per LED theme
   and warmed at start-up.

## 2026-10-30 — Hold the design system with tests

**Problem.** After three rounds of features the UI had drifted: 47 sizes written as
literals, 21 tokens and 5 classes nobody used, a 720px breakpoint beside the listed
ones, warning text at 4.0:1 contrast, rows whose text started at different edges,
buttons of four kinds for the same weight of action, a control inside a link, raw
`urlopen` errors and launchctl lines shown to users, and the device bar drawing social
apps as initials while their rows drew their marks.

**Choices.**
1. `docs/design-system.md` states the tokens, components, layout and contrast rules;
   `tests/test_design_system.py` fails on a literal colour or size, an unknown or unused
   token, an unlisted breakpoint, or text under 4.5:1 on any surface in either theme.
2. Rows without an icon line up with rows that have one; list rows link by their title,
   stretched over the row, with the placement button beside it.
3. One button hierarchy: a primary per area, outlined buttons with icons for other
   actions, ghost for text-like links and heading actions.
4. Errors say what to check; the technical reason moves to the tooltip.
5. Built-in apps the browser does not simulate show the server's picture in the device
   bar too, so each app has one picture everywhere.
