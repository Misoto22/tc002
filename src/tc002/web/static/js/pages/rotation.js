import { appName, t } from "../i18n.js";
import { sortable } from "../sortable.js";
import { edit, setFocus, show, store } from "../store.js";
import { button, h, icon, menu, pageHead, panel, row, section, toggle } from "../ui.js";
import { page, thumb } from "./common.js";

export function playlist() {
  setFocus({ type: "playlist" });
  const d = store.draft;
  const slots = d.playlist.slots;
  const total = slots.reduce((sum, s) => sum + Number(s.seconds), 0);

  const list = h("div", { class: "panel slots", "data-path": "playlist.slots" });
  slots.forEach((slot, i) => {
    const key = slot.screen ?? slot.builtin;
    list.append(h("div", {
      class: "row slot", tabindex: "0", "data-index": i,
      "aria-label": `${appName(key)}, ${slot.seconds} ${t("playlist.seconds")}`,
    },
    h("span", { class: "handle", title: t("playlist.drag") }, icon("grip-vertical")),
    thumb(key, Boolean(slot.screen)),
    h("div", { class: "row-text" },
      h("div", { class: "row-title" }, appName(key)),
      h("div", { class: "row-hint" }, slot.screen ? t("playlist.screen") : t("playlist.builtin"))),
    h("div", { class: "row-control" },
      h("div", { class: "seconds" },
        h("input", { class: "field num", type: "number", min: 3, max: 600, value: slot.seconds,
          "aria-label": `${appName(key)} ${t("playlist.seconds")}`,
          onChange: (e) => edit((dr) => { dr.playlist.slots[i].seconds = Math.max(3, Number(e.target.value) || 3); }) }),
        h("span", { class: "muted" }, "s")),
      button("", () => show(slot.screen ? { screen: key } : { builtin: key }), { kind: "ghost icon", ico: "eye", title: t("btn.showNow") }),
      button("", () => edit((dr) => { dr.playlist.slots.splice(i, 1); }, { rerender: true }), { kind: "ghost icon", ico: "x", title: t("btn.remove") }))));
  });
  if (!slots.length) list.append(h("div", { class: "empty" }, icon("list-video"), t("playlist.empty")));
  sortable(list, (order) => edit((dr) => { dr.playlist.slots = order.map((i) => slots[i]); }, { rerender: true }));

  const add = button(t("btn.addSlot"), (e) => menu(e.currentTarget, [
    [t("playlist.screens"), d.screens.enabled.map((s) => [{ screen: s }, appName(s), "sparkles"])],
    [t("playlist.builtins"), d.device.keep_builtins.map((b) => [{ builtin: b }, appName(b), "blocks"])],
  ], (pick) => edit((dr) => { dr.playlist.slots.push({ ...pick, seconds: 15 }); }, { rerender: true }),
  t("playlist.nothing")), { ico: "plus" });

  const cycle = h("div", { class: "cycle", "aria-hidden": "true" },
    ...slots.map((s, i) => h("span", { style: `flex:${s.seconds};--hue:${235 + i * 37}` })));

  return page(
    pageHead(t("page.playlist"), t("desc.playlist"), add),
    list,
    slots.length ? h("div", { class: "cycle-wrap" }, cycle, h("div", { class: "row-hint" }, t("playlist.cycle", { s: total }))) : null,
    section(t("section.behaviour")),
    panel(
      row(t("playlist.takeover"), t("playlist.takeoverHint"),
        toggle(d.alerts.takeover, (v) => edit((dr) => { dr.alerts.takeover = v; }), { label: t("playlist.takeover") }),
        { path: "alerts.takeover", icon: "bell" }),
      ...store.state.screens.map((s) => row(t("playlist.screenToggle", { name: appName(s) }), t("playlist.screenHint"),
        toggle(d.screens.enabled.includes(s), (on) => edit((dr) => {
          dr.screens.enabled = on ? [...dr.screens.enabled, s] : dr.screens.enabled.filter((x) => x !== s);
          if (!on) dr.playlist.slots = dr.playlist.slots.filter((x) => x.screen !== s);
        }, { rerender: true }), { label: appName(s) }),
        { path: "screens.enabled", icon: s === "claude" ? "bot" : "cpu" })),
    ),
  );
}
