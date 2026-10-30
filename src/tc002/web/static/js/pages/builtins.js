// The clock's own apps: each with a picture of what it shows and where it shows; the row
// opens the app's own page with its settings (city, format, account).

import { appName, t } from "../i18n.js";
import { placementButton, placementOf } from "../placement.js";
import { setFocus, store } from "../store.js";
import { appIcon, h, icon, pageHead, section } from "../ui.js";
import { offlineNotice, page, thumb } from "./common.js";
import { appSettings } from "./builtin-settings.js";

function appItem(key) {
  const live = store.state.clock.builtins ?? {};
  const href = `#builtins/${key}`;
  const hints = [];
  if (live[key]) hints.push(live[key].enabled ? t("builtins.onNow") : t("builtins.offNow"));
  if (live[key]?.credentials) hints.push(t("builtins.linked"));
  if (appSettings(key).length) hints.push(t("builtins.hasSettings"));
  const p = placementOf("builtin", key);
  return h("div", {
    class: `row library-row link-row${p === "off" ? "" : " on"}`, "data-path": "device.keep_builtins",
    onFocusin: () => setFocus({ type: "builtin", key }),
  },
  thumb(key, false),
  h("div", { class: "row-text" },
    h("div", { class: "row-title" }, appIcon(key, "sm"), h("a", { class: "row-link", href }, appName(key))),
    h("div", { class: "row-hint" }, hints.join(" · "))),
  h("div", { class: "row-control" }, placementButton("builtin", key, href), icon("chevron-right", "icon faint")));
}

export function builtins() {
  if (store.focus.type !== "builtin") setFocus({ type: "builtin", key: "clock" });
  const groups = ["tools", "social", "calendar"].flatMap((cat) => {
    const apps = store.state.catalogue.filter((a) => a.category === cat);
    return [section(t(`builtins.cat.${cat}`)), h("div", { class: "panel library" }, ...apps.map(({ key }) => appItem(key)))];
  });
  return page(pageHead(t("page.builtins"), t("desc.builtins")),
    store.state.clock.online ? null : offlineNotice(store.state.clock), ...groups);
}
