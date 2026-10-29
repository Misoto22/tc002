// The clock's own apps: each with a picture of what it shows, a switch, and its settings
// right under it (city, format, account), so keeping an app and setting it up is one place.

import { appName, t } from "../i18n.js";
import { edit, setFocus, store } from "../store.js";
import { appIcon, badge, h, icon, pageHead, section, toggle } from "../ui.js";
import { offlineNotice, page, thumb } from "./common.js";
import { appSettings } from "./builtin-settings.js";

function appItem(key, inRotation) {
  const d = store.draft;
  const live = store.state.clock.builtins ?? {};
  const kept = d.device.keep_builtins.includes(key);
  const used = inRotation.has(key);
  const settings = appSettings(key);
  const hints = [];
  if (live[key]) hints.push(live[key].enabled ? t("builtins.onNow") : t("builtins.offNow"));
  if (live[key]?.credentials) hints.push(t("builtins.linked"));
  if (!kept && settings.length) hints.push(t("builtins.offHint"));
  const focus = () => setFocus({ type: "builtin", key });
  return h("div", { class: `library-item${kept ? " on" : ""}`, "data-path": "device.keep_builtins", onPointerdown: focus, onFocusin: focus },
    h("div", { class: "row library-row" },
      thumb(key, false),
      h("div", { class: "row-text" },
        h("div", { class: "row-title" }, appIcon(key, "sm"), appName(key), used ? badge(t("builtins.inUse"), "ok") : null),
        h("div", { class: "row-hint" }, hints.join(" · "))),
      h("div", { class: "row-control" },
        settings.length && !kept ? icon("sliders-horizontal", "icon faint") : null,
        toggle(kept, (on) => edit((dr) => {
          dr.device.keep_builtins = on ? [...dr.device.keep_builtins, key] : dr.device.keep_builtins.filter((k) => k !== key);
        }, { rerender: true }), { label: appName(key), disabled: used && kept }))),
    kept && settings.length ? h("div", { class: "library-options" }, ...settings) : null);
}

export function builtins() {
  if (store.focus.type !== "builtin") setFocus({ type: "builtin", key: "clock" });
  const d = store.draft;
  const held = d.rotation.mode === "single" ? [d.rotation.show] : [];
  const inRotation = new Set([...d.rotation.slots, ...held].filter(Boolean).map((s) => s.builtin).filter(Boolean));
  const groups = ["tools", "social", "calendar"].flatMap((cat) => {
    const apps = store.state.catalogue.filter((a) => a.category === cat);
    return [section(t(`builtins.cat.${cat}`)), h("div", { class: "panel library" }, ...apps.map(({ key }) => appItem(key, inRotation)))];
  });
  return page(pageHead(t("page.builtins"), t("desc.builtins")),
    store.state.clock.online ? null : offlineNotice(store.state.clock), ...groups);
}
