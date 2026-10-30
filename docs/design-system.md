# Design system

The UI is paper, ink and one accent: quiet surfaces, text that carries the hierarchy,
and colour reserved for state. Everything below is enforced by
`tests/test_design_system.py` unless marked otherwise.

## Tokens

`src/tc002/web/static/css/tokens.css` is the only place a colour or a size is written.
Rules in `base.css`, `components.css`, `pages.css` and `motion.css` use `var(--…)` only
(`0` and `1px` hairlines aside); a token nobody uses is deleted, and a token used must
exist. `palettes.css` overrides colours per UI palette; the LED themes for the clock are
in `render/themes.py`.

| Group | Tokens | Use |
|---|---|---|
| Surfaces | `--bg`, `--panel`, `--panel-raised`, `--field`, `--sidebar`, `--glass` | page, cards, menus, inputs |
| Text | `--text`, `--text-2`, `--muted`, `--faint` | strongest to quietest; all pass AA on every surface |
| State | `--green`, `--yellow`, `--red`, `--accent` (+ `-soft`) | status dots, warnings, the chosen item |
| Agents | `--agent-claude`, `--agent-codex` | the two agents' marks only |
| Space | `--space-N` (N is its px) | every padding, margin and gap |
| Shape | `--radius-*`, `--hairline`, `--hairline-mid`, `--hairline-strong`, `--ring`, `--focus-w` | corners, rules, outlines, focus |
| Size | `--control-h` 32, `--control-sm-h` 26, `--control-xs-h` 20, `--row-h` 56, `--icon*`, `--app-icon*`, `--dot*` | controls and marks |
| Type | `--font`, `--display`, `--mono`, `--text-xs` … `--text-2xl` | one sans, one mono |

## Components

- **Panel** (`.panel`): a card of **rows**. A rule only ever separates rows inside a card;
  nothing draws a free-standing line on the page. In a panel where some rows have an
  icon, rows without one indent to the same text edge.
- **Row** (`row()` in `ui.js`): icon · title and hint · controls on the right. On a phone
  the controls take their own line under the title.
- **List row that opens a page** (`.link-row`): the title is the link, stretched over the
  row; the placement button beside it is a separate control (no control inside a link).
- **Card** (`.live-card`, `.choice`, `.screen-card`, `.game-card`): a picture first, then
  its words. Every item's page opens with a `.live-card`.
- **Buttons**: one `primary` per area (the main action: Start, Save, Connect, Install);
  every other action is the default outlined button with an icon (Test, Restart, Remove);
  `ghost` is for links that read as text (Settings…, Change →), actions inside a heading
  line (Read again, Add slot, Search again) and icon-only row actions.
- **Placement**: "Where it shows" has the same four answers everywhere — off, kept, in
  the rotation, shown alone — as a menu on list rows and a segmented control on pages.
- **Icons**: Lucide glyphs and brand marks with no tile behind them, sized by `--icon*`
  and `--app-icon*`; only the agents' marks are coloured.
- **Pictures of the clock**: always the LED mock-up (`.led-thumb`), drawn by the server
  from the same renderer the clock uses; a picture that is an imitation says so once.
- **Errors** are sentences that say what to check; the technical reason sits in the
  tooltip (`clockProblem`, `serviceSummary` in `pages/common.js`). *(Not tested.)*

## Layout

- Content is at most `--content-w` wide, centred; every page starts with a `pageHead`,
  an item's page with a breadcrumb above it.
- Breakpoints: 640px, 760px (phone: the sidebar becomes an icon rail, rows wrap) and
  900px (the preview stacks). No other width appears in a media query.
- No page scrolls sideways at 375px. *(Checked in the browser, not in CI.)*

## Contrast and access

- Text tokens reach WCAG AA (4.5:1) on `--bg`, `--panel` and `--field`, light and dark.
- Keyboard focus is a `--focus-w` outline in `--accent`; every list row is reachable by
  Tab. Icon-only buttons carry an `aria-label`. *(Not tested.)*

## Motion

A page draws at once with one short fade (`--fast`); nothing waits its turn. A theme
change spreads from the control that made it. Everything stops for
`prefers-reduced-motion`.
