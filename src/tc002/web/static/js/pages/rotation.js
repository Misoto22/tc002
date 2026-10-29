// What the clock shows: the display mode (rotate through slots, or hold one screen), the
// slots or the pick, templates, then the screen library and how alerts behave.

import { ago, appName, t } from "../i18n.js";
import { sortable } from "../sortable.js";
import { applyPreset, edit, setFocus, show, store } from "../store.js";
import { appIcon, button, h, icon, menu, pageHead, section } from "../ui.js";
import { page, slotKey, thumb } from "./common.js";
import { behaviour, library } from "./library.js";

const clampSeconds = (v) => {
  const { min, max } = store.state.slotSeconds;
  return Math.min(max, Math.max(min, Number(v) || min));
};
const same = (a, b) => JSON.stringify(a.map(slotKey)) === JSON.stringify(b.map(slotKey));
const isSingle = (d) => d.rotation.mode === "single";

// Everything the clock could show: enabled screens, then kept built-in apps.
export function choices(d = store.draft) {
  return [...d.screens.enabled.map((screen) => ({ screen })), ...d.device.keep_builtins.map((builtin) => ({ builtin }))];
}

function modeCard(mode, ico) {
  const d = store.draft;
  const pressed = (d.rotation.mode ?? "cycle") === mode;
  return h("button", {
    type: "button", class: "choice mode-choice", "aria-pressed": String(pressed),
    onClick: () => edit((dr) => {
      if (mode === "single") {
        dr.rotation.mode = "single";
        const first = dr.rotation.slots[0] ?? choices(dr)[0];
        if (!dr.rotation.show && first) dr.rotation.show = first.screen ? { screen: first.screen } : { builtin: first.builtin };
      } else { // rotating again: the pin is forgotten, so it holds nothing back
        delete dr.rotation.mode;
        delete dr.rotation.show;
      }
    }, { rerender: true }),
  }, h("span", { class: "choice-head" }, icon(ico), h("span", { class: "choice-title" }, t(`mode.${mode}`))),
  h("span", { class: "muted" }, t(`mode.${mode}Hint`)));
}

function summary() {
  const d = store.draft;
  const slots = d.rotation.slots;
  let text;
  if (isSingle(d) && d.rotation.show) text = t("mode.nowSingle", { name: appName(slotKey(d.rotation.show)) });
  else if (!slots.length) text = t("mode.nowEmpty");
  else text = t("mode.nowCycle", { n: slots.length, s: slots.reduce((sum, s) => sum + Number(s.seconds), 0) });
  return h("p", { class: "mode-summary" }, icon("info"), text, h("span", { class: "muted" }, ` ${t("mode.alertsNote")}`));
}

// ---- rotate -------------------------------------------------------------------------

function freshnessHint(key) {
  const f = store.state.freshness?.[key];
  if (!f || f.age === null && !f.stale) return h("div", { class: "row-hint" }, t("rotation.screen"));
  if (f.stale) {
    const text = f.age === null ? t("fresh.never", { error: f.error }) : t("fresh.stale", { ago: ago(f.age), error: f.error });
    return h("div", { class: "row-hint warn" }, text);
  }
  return h("div", { class: "row-hint" }, t("fresh.ok", { ago: ago(f.age) }));
}

function slotRow(slot, i) {
  const key = slotKey(slot);
  const focus = () => setFocus(slot.screen ? { type: "screen", key } : { type: "builtin", key });
  return h("div", {
    class: "row slot", tabindex: "0", "data-index": i, onFocusin: focus,
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

function cycleBlock() {
  const d = store.draft;
  const slots = d.rotation.slots;
  const list = h("div", { class: "panel slots", "data-path": "rotation.slots" }, ...slots.map(slotRow));
  if (!slots.length) list.append(h("div", { class: "empty" }, icon("repeat"), t("rotation.empty")));
  sortable(list, (order) => edit((dr) => { dr.rotation.slots = order.map((i) => slots[i]); }, { rerender: true }));
  const inList = new Set(slots.map(slotKey));
  const add = button(t("btn.addSlot"), (e) => menu(e.currentTarget, [
    [t("rotation.screens"), d.screens.enabled.filter((s) => !inList.has(s)).map((s) => [{ screen: s }, appName(s), null, s])],
    [t("rotation.builtins"), d.device.keep_builtins.filter((b) => !inList.has(b)).map((b) => [{ builtin: b }, appName(b), null, b])],
  ], (pick) => edit((dr) => { dr.rotation.slots.push({ ...pick, seconds: 15 }); }, { rerender: true }),
  t("rotation.nothing")), { ico: "plus", kind: "ghost" });
  return [
    section(t("rotation.slots"), h("span", { class: "spacer" }), add),
    list,
    section(t("mode.templates"), h("span", { class: "muted" }, `· ${t("mode.templatesHint")}`)),
    h("div", { class: "presets" }, ...store.state.presets.map((p) => h("button", {
      class: `preset${same(p.slots, slots) ? " current" : ""}`, type: "button", onClick: () => applyPreset(p.id),
    },
    h("div", { class: "preset-icons" }, ...p.slots.map((s) => appIcon(slotKey(s), "sm"))),
    h("div", { class: "preset-name" }, t(`preset.${p.id}.name`)),
    h("div", { class: "preset-desc" }, t(`preset.${p.id}.desc`))))),
  ];
}

// ---- show one -----------------------------------------------------------------------

function singleBlock() {
  const d = store.draft;
  const options = choices(d);
  const current = d.rotation.show ? slotKey(d.rotation.show) : null;
  return [
    section(t("mode.pick")),
    options.length ? h("div", { class: "screen-grid", "data-path": "rotation.show", role: "radiogroup" }, ...options.map((o) => {
      const key = slotKey(o);
      return h("button", {
        type: "button", class: "screen-card", role: "radio", "aria-checked": String(key === current),
        onClick: () => edit((dr) => { dr.rotation.show = { ...o }; }, { rerender: true }),
        onFocus: () => setFocus(o.screen ? { type: "screen", key } : { type: "builtin", key }),
      }, thumb(key, Boolean(o.screen)),
      h("span", { class: "screen-card-title" }, appIcon(key, "sm"), appName(key),
        key === current ? icon("circle-check", "icon screen-card-check") : null));
    })) : h("div", { class: "panel" }, h("div", { class: "empty" }, icon("pin"), t("mode.pickEmpty"))),
  ];
}

export function rotation() {
  if (store.focus.type !== "screen" && store.focus.type !== "builtin") setFocus({ type: "rotation" });
  const d = store.draft;
  return page(
    pageHead(t("page.rotation"), t("desc.rotation")),
    section(t("mode.title")),
    h("div", { class: "choices mode-choices", "data-path": "rotation.mode" }, modeCard("cycle", "repeat"), modeCard("single", "pin")),
    summary(),
    ...(isSingle(d) ? singleBlock() : cycleBlock()),
    ...library(),
    ...behaviour(),
  );
}
