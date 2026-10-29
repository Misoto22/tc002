// tc002's own screens, each with its picture, a line on what it shows and where it shows;
// and how alerts behave, shown with the alert itself. Part of the On the clock page.

import { appName, t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { placementButton, placementOf } from "../placement.js";
import { appIcon, h, icon, panel, row, section, toggle } from "../ui.js";
import { thumb } from "./common.js";

// One screen: its picture and a line on what it shows; the row opens its own page, the
// button on the right says (and changes) where it shows.
function screenRow(name) {
  const p = placementOf("screen", name);
  const href = `#rotation/${name}`;
  return h("a", {
    class: `row library-row link-row${p === "off" ? "" : " on"}`, href, "data-path": "screens.enabled",
    onFocus: () => setFocus({ type: "screen", key: name }),
  },
  thumb(name, true),
  h("div", { class: "row-text" },
    h("div", { class: "row-title" }, appIcon(name, "sm"), appName(name),
      store.state.networked.includes(name) ? h("span", { class: "tag" }, t("library.networked")) : null),
    h("div", { class: "row-hint" }, t(`screen.${name}`))),
  h("div", { class: "row-control" }, placementButton("screen", name, href), icon("chevron-right", "icon faint")));
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
