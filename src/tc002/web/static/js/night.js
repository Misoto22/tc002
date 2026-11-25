// Night: the clock's screen fully dark, on a schedule (tc002.toml [night], saved like any
// other setting) or right now (POST /api/night, applied at once). Times are this Mac's.
// Shared by the Display page, the quick-settings popover and the Overview.

import { post } from "./api.js";
import { t, until } from "./i18n.js";
import { edit, load, store } from "./store.js";
import { badge, button, h, icon, panel, row, section, toast, toggle } from "./ui.js";

const DEFAULTS = { enable: false, start: "23:00", end: "07:00" };
const now = () => store.state.night ?? { dark: false, why: null, schedule: DEFAULTS };
const schedule = () => ({ ...DEFAULTS, ...store.draft.night });
const clockTime = (unix) => new Date(unix * 1000).toTimeString().slice(0, 5);

async function setOff(off) {
  try {
    await post("/api/night", { off, until: off && schedule().enable ? "morning" : null });
    await load();
  } catch (err) {
    toast(err.title, err.message, "error");
  }
}

// One line on what the screen is doing now, e.g. "Screen off · lights at 07:00".
export function nightLine() {
  const n = now();
  const at = n.until ? clockTime(n.until) : null;
  if (n.why === "off") return at ? t("night.lineOffUntil", { at, left: until(n.until) ?? "" }) : t("night.lineOffManual");
  if (n.why === "schedule") return t("night.lineScheduled", { at });
  if (n.why === "on") return t("night.lineKeptOn", { at });
  return at ? t("night.lineNext", { at }) : t("night.lineOn");
}

// The "screen off" switch: in the quick popover (compact) and on the Display page.
export function nightSwitch({ compact = false } = {}) {
  const n = now();
  const sched = schedule();
  const control = toggle(n.dark, (off) => setOff(off),
    { label: t("night.offNow"), disabled: !store.state.clock.online });
  const hint = sched.enable ? t("night.offNowHintMorning", { end: sched.end }) : t("night.offNowHint");
  return h("div", { class: compact ? "quick-row" : "row" },
    h("span", { class: "row-icon" }, icon("moon")),
    compact ? h("div", { class: "row-title" }, t("night.offNow"))
      : h("div", { class: "row-text" },
        h("div", { class: "row-title" }, t("night.offNow")),
        h("div", { class: "row-hint" }, `${hint} · ${nightLine()}`)),
    h("div", { class: "row-control" }, control));
}

function timeInput(value, onChange, label) {
  return h("input", {
    class: "field", type: "time", value, "aria-label": label, required: true,
    onChange: (e) => e.currentTarget.value && onChange(e.currentTarget.value),
  });
}

// Display page: the switch, and the schedule (saved with the rest of tc002.toml).
export function nightSection() {
  const sched = schedule();
  const set = (patch) => edit((dr) => { dr.night = { ...sched, ...patch }; }, { rerender: true });
  const n = now();
  return [
    section(t("night.title"), h("span", { class: "spacer" }),
      badge(n.dark ? t("night.badgeDark") : t("night.badgeOn"), n.dark ? "warn" : "ok")),
    panel(
      nightSwitch(),
      row(t("night.schedule"), t("night.scheduleHint"),
        toggle(sched.enable, (v) => set({ enable: v }), { label: t("night.schedule") }),
        { path: "night", icon: "moon-star" }),
      row(t("night.hours"), t("night.hoursHint"),
        [timeInput(sched.start, (v) => set({ start: v }), t("night.from")),
          h("span", { class: "muted" }, "→"),
          timeInput(sched.end, (v) => set({ end: v }), t("night.to"))],
        { path: "night", icon: "clock" }),
    ),
  ];
}

// Overview: a notice while the screen is dark, so a black clock never looks broken.
export function nightNotice() {
  const n = now();
  if (!n.dark) return null;
  return panel(row(t("night.title"), nightLine(),
    button(t("night.turnOn"), () => setOff(false), { kind: "primary", ico: "sun" }),
    { icon: "moon" }));
}
