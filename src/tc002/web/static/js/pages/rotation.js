import { ago, appName, t } from "../i18n.js";
import { sortable } from "../sortable.js";
import { applyPreset, edit, setFocus, show, store } from "../store.js";
import { appIcon, button, h, icon, menu, pageHead, panel, row, section, toggle } from "../ui.js";
import { page, thumb } from "./common.js";

const slotKey = (s) => s.screen ?? s.builtin;
const clampSeconds = (v) => {
  const { min, max } = store.state.slotSeconds;
  return Math.min(max, Math.max(min, Number(v) || min));
};
const same = (a, b) => JSON.stringify(a.map(slotKey)) === JSON.stringify(b.map(slotKey));

function presetCards(slots) {
  return h("div", { class: "presets" }, ...store.state.presets.map((p) => h("button", {
    class: `preset${same(p.slots, slots) ? " current" : ""}`, type: "button",
    onClick: () => applyPreset(p.id),
  },
  h("div", { class: "preset-icons" }, ...p.slots.map((s) => appIcon(slotKey(s), "sm"))),
  h("div", { class: "preset-name" }, t(`preset.${p.id}.name`)),
  h("div", { class: "preset-desc" }, t(`preset.${p.id}.desc`)))));
}

// How fresh a tc002 screen's data is, as the background service last recorded it.
function freshnessHint(key) {
  const f = store.state.freshness?.[key];
  if (!f) return h("div", { class: "row-hint" }, t("rotation.screen"));
  if (f.stale) {
    const text = f.age === null ? t("fresh.never", { error: f.error }) : t("fresh.stale", { ago: ago(f.age), error: f.error });
    return h("div", { class: "row-hint warn" }, text);
  }
  return h("div", { class: "row-hint" }, f.age === null ? t("rotation.screen") : t("fresh.ok", { ago: ago(f.age) }));
}

function slotRow(slot, i) {
  const key = slotKey(slot);
  return h("div", {
    class: "row slot", tabindex: "0", "data-index": i,
    "aria-label": `${appName(key)}, ${slot.seconds} ${t("rotation.seconds")}`,
  },
  h("span", { class: "handle", title: t("rotation.drag") }, icon("grip-vertical")),
  thumb(key, Boolean(slot.screen)),
  h("div", { class: "row-text" },
    h("div", { class: "row-title" }, appIcon(key, "sm"), appName(key)),
    slot.screen ? freshnessHint(key) : h("div", { class: "row-hint" }, t("rotation.builtin"))),
  h("div", { class: "row-control" },
    h("div", { class: "seconds" },
      h("input", { class: "field num", type: "number", min: store.state.slotSeconds.min, max: store.state.slotSeconds.max, value: slot.seconds,
        "aria-label": `${appName(key)} ${t("rotation.seconds")}`,
        onChange: (e) => edit((dr) => { dr.rotation.slots[i].seconds = clampSeconds(e.target.value); }) }),
      h("span", { class: "muted" }, t("unit.seconds"))),
    button("", () => show(slot.screen ? { screen: key } : { builtin: key }), { kind: "ghost icon", ico: "eye", title: t("btn.showNow") }),
    button("", () => edit((dr) => { dr.rotation.slots.splice(i, 1); }, { rerender: true }), { kind: "ghost icon", ico: "x", title: t("btn.remove") })));
}

export function rotation() {
  setFocus({ type: "rotation" });
  const d = store.draft;
  const slots = d.rotation.slots;
  const total = slots.reduce((sum, s) => sum + Number(s.seconds), 0);

  const list = h("div", { class: "panel slots", "data-path": "rotation.slots" }, ...slots.map(slotRow));
  if (!slots.length) list.append(h("div", { class: "empty" }, icon("repeat"), t("rotation.empty")));
  sortable(list, (order) => edit((dr) => { dr.rotation.slots = order.map((i) => slots[i]); }, { rerender: true }));

  const add = button(t("btn.addSlot"), (e) => menu(e.currentTarget, [
    [t("rotation.screens"), d.screens.enabled.map((s) => [{ screen: s }, appName(s), null, s])],
    [t("rotation.builtins"), d.device.keep_builtins.map((b) => [{ builtin: b }, appName(b), null, b])],
  ], (pick) => edit((dr) => { dr.rotation.slots.push({ ...pick, seconds: 15 }); }, { rerender: true }),
  t("rotation.nothing")), { ico: "plus" });

  // one segment per slot, sized by its seconds
  const cycle = h("div", { class: "cycle", "aria-hidden": "true" },
    ...slots.map((s) => h("span", { style: `flex:${s.seconds}` })));

  return page(
    pageHead(t("page.rotation"), t("desc.rotation"), add),
    section(t("rotation.presets"), h("span", { class: "muted" }, `· ${t("rotation.presetsHint")}`)),
    presetCards(slots),
    section(t("rotation.slots")),
    list,
    slots.length ? h("div", { class: "cycle-wrap" }, cycle, h("div", { class: "row-hint" }, t("rotation.cycle", { s: total }))) : null,
    section(t("section.behaviour")),
    panel(
      row(t("rotation.takeover"), t("rotation.takeoverHint"),
        toggle(d.alerts.takeover, (v) => edit((dr) => { dr.alerts.takeover = v; }), { label: t("rotation.takeover") }),
        { path: "alerts.takeover", icon: "bell" }),
      ...store.state.screens.map((s) => row(t("rotation.screenToggle", { name: appName(s) }), t("rotation.screenHint"),
        toggle(d.screens.enabled.includes(s), (on) => edit((dr) => {
          dr.screens.enabled = on ? [...dr.screens.enabled, s] : dr.screens.enabled.filter((x) => x !== s);
          if (!on) dr.rotation.slots = dr.rotation.slots.filter((x) => x.screen !== s);
        }, { rerender: true }), { label: appName(s) }),
        { path: "screens.enabled", app: s })),
    ),
  );
}
