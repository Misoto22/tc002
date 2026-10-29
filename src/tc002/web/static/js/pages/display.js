import { t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { badge, pageHead, panel, row, section, segmented, select, slider, toggle } from "../ui.js";
import { offlineNotice, page } from "./common.js";
import { ledThemes } from "../appearance.js";

const ICONS = { volume: "bell", timezone: "clock", dateFormat: "history", showWeek: "history",
  weekStart: "history", scrollSpeed: "zap", lowBatteryAutoSleep: "power" };

// Where a value comes from: the clock itself, or tc002.toml (and whether the clock has it yet).
function managed(key, clockValue) {
  if (!(key in store.draft.display)) return t("display.fromClock");
  const want = store.draft.display[key];
  const differs = store.state.clock.online && (want && typeof want === "object"
    ? Object.entries(want).some(([k, v]) => clockValue?.[k] !== v)
    : clockValue !== want);
  return { text: differs ? t("display.pending") : t("display.inToml"), warn: differs };
}

export function display() {
  setFocus({ type: "builtin", key: "clock" });
  const clock = store.state.clock.settings ?? {};
  const schema = store.state.schema;
  const value = (key) => store.draft.display[key] ?? clock[key];
  const set = (key, v) => edit((dr) => { dr.display[key] = v; });
  const bright = { ...schema.brightnessDefaults, ...clock.brightness, ...store.draft.display.brightness };
  const setBright = (patch) => { Object.assign(bright, patch); edit((dr) => { dr.display.brightness = { ...bright }; }); };
  const levels = schema.brightnessLevels;

  const rows = Object.entries(schema.display).map(([key, rule]) => {
    const label = t(`field.${key}`);
    let control;
    if (rule.kind === "bool") control = toggle(value(key), (v) => set(key, v), { label });
    else if (rule.kind === "int") control = slider(rule.options[0], rule.options[1], value(key) ?? rule.options[0], (v) => set(key, v), label);
    else if (key === "weekStart") control = segmented([[1, t("day.monday")], [0, t("day.sunday")]], value(key), (v) => set(key, v), label);
    else if (rule.options.length <= 3) control = segmented(rule.options.map((o) => [o, o]), value(key), (v) => set(key, v), label);
    else control = select(rule.options.map((o) => [o, o]), value(key), (v) => set(key, v), label);
    return row(label, managed(key, clock[key]), control, { path: `display.${key}`, icon: ICONS[key] });
  });

  const r = store.draft.rotation;
  const hasRotation = r.mode === "single" ? Boolean(r.show) : r.slots.length > 0;
  return page(
    pageHead(t("page.display"), t("desc.display")),
    store.state.clock.online ? null : offlineNotice(store.state.clock),
    ...ledThemes(() => document.getElementById("page").replaceChildren(display())),
    section(t("section.brightness")),
    panel(
      row(t("display.level"), managed("brightness", clock.brightness),
        segmented(levels.map((l) => [l, t(`level.${l}`)]), bright.level, (v) => setBright({ level: v }), t("display.level")),
        { path: "display.brightness", icon: "sun" }),
      ...levels.map((l) => row(t("display.levelPercent", { level: t(`level.${l}`) }), t("display.percentHint"),
        slider(...schema.brightnessRange, bright[l], (v) => setBright({ [l]: v }), l), { path: "display.brightness" })),
    ),
    section(t("section.general")),
    panel(...rows,
      row(t("display.carousel"), hasRotation ? t("display.carouselOff") : t("display.carouselDevice"),
        badge(hasRotation ? t("display.rotationBadge") : `${clock.carouselSpeed ?? "?"}s`), { icon: "repeat" })),
  );
}
