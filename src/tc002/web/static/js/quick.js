// Quick settings: the controls people reach for most (brightness, volume), applied to the
// clock at once. Shared by the top-bar popover and the overview page.

import { t } from "./i18n.js";
import { quick, store } from "./store.js";
import { attachPopover, h, icon, segmented, slider } from "./ui.js";

function current() {
  const clock = store.state.clock.settings ?? {};
  const display = store.saved.display ?? {};
  return {
    brightness: { level: "high", low: 50, mid: 80, high: 100, ...clock.brightness, ...display.brightness },
    volume: display.volume ?? clock.volume ?? 0,
  };
}

export function quickControls({ compact = false } = {}) {
  const now = current();
  const levels = store.state.schema.brightnessLevels;
  const percent = h("div", {});
  const renderPercent = () => percent.replaceChildren(slider(5, 100, now.brightness[now.brightness.level],
    (v) => { now.brightness[now.brightness.level] = v; quick({ brightness: { ...now.brightness } }); },
    t("quick.brightness")));
  renderPercent();
  const volumeRange = store.state.schema.display.volume.options;
  const rowClass = compact ? "quick-row" : "row";
  return [
    h("div", { class: rowClass },
      h("span", { class: "row-icon" }, icon("sun-dim")),
      h("div", { class: "row-title" }, t("quick.brightness")),
      segmented(levels.map((l) => [l, t(`level.${l}`)]), now.brightness.level,
        (level) => { now.brightness.level = level; quick({ brightness: { ...now.brightness } }); renderPercent(); },
        t("quick.brightness")),
      percent),
    h("div", { class: rowClass },
      h("span", { class: "row-icon" }, icon("volume-2")),
      h("div", { class: "row-title" }, t("quick.volume")),
      slider(volumeRange[0], volumeRange[1], now.volume, (v) => quick({ volume: v }), t("quick.volume"))),
  ];
}

// The top-bar popover.
export function openQuick(anchor) {
  document.querySelector(".popover.quick")?.remove();
  let close = () => {};
  const el = h("div", { class: "popover quick", role: "dialog", "aria-label": t("quick.title") },
    h("div", { class: "menu-label" }, t("quick.title")),
    ...quickControls({ compact: true }),
    h("a", { class: "btn ghost", href: "#display", onClick: () => close() }, icon("sliders-horizontal"), t("quick.more")));
  close = attachPopover(el, anchor);
  el.querySelector("button")?.focus();
}
