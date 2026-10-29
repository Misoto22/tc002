// tc002's own screens, each with its picture, a line on what it shows, a switch and its
// options; and how alerts behave, shown with the alert itself. Part of the On the clock page.

import { appName, t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { appIcon, badge, h, panel, row, section, toggle } from "../ui.js";
import { screenOptions } from "./screen-options.js";
import { thumb } from "./common.js";

function setEnabled(name, on) {
  edit((dr) => {
    dr.screens.enabled = on ? [...dr.screens.enabled, name] : dr.screens.enabled.filter((x) => x !== name);
    if (on) return;
    dr.rotation.slots = dr.rotation.slots.filter((x) => x.screen !== name);
    if (dr.rotation.show?.screen === name) { // the held screen went away: rotate again
      delete dr.rotation.show;
      delete dr.rotation.mode;
    }
  }, { rerender: true });
}

function screenRow(name) {
  const d = store.draft;
  const on = d.screens.enabled.includes(name);
  const used = d.rotation.slots.some((s) => s.screen === name) || d.rotation.show?.screen === name;
  const focus = () => setFocus({ type: "screen", key: name });
  const options = on ? screenOptions(name) : null;
  return h("div", { class: `library-item${on ? " on" : ""}`, "data-path": "screens.enabled", onPointerdown: focus, onFocusin: focus },
    h("div", { class: "row library-row" },
      thumb(name, true),
      h("div", { class: "row-text" },
        h("div", { class: "row-title" }, appIcon(name, "sm"), appName(name),
          used ? badge(t("library.inRotation"), "ok") : null,
          store.state.networked.includes(name) ? h("span", { class: "tag" }, t("library.networked")) : null),
        h("div", { class: "row-hint" }, t(`screen.${name}`))),
      h("div", { class: "row-control" }, toggle(on, (v) => setEnabled(name, v), { label: appName(name) }))),
    options ? h("div", { class: "library-options" }, ...options) : null);
}

export function library() {
  return [
    section(t("library.title"), h("span", { class: "muted" }, `· ${t("library.hint")}`)),
    h("div", { class: "panel library" }, ...store.state.screens.map(screenRow)),
  ];
}

// "Alerts take over", next to the alert it brings up.
export function behaviour() {
  const d = store.draft;
  return [
    section(t("section.behaviour")),
    panel(row(t("rotation.takeover"),
      t("behaviour.takeoverHint"),
      [h("figure", { class: "example" }, thumb("claude-wait", true), h("figcaption", {}, t("behaviour.example"))),
        toggle(d.alerts.takeover, (v) => edit((dr) => { dr.alerts.takeover = v; }), { label: t("rotation.takeover") })],
      { path: "alerts.takeover", icon: "bell" })),
  ];
}
