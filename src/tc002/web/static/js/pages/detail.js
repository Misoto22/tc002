// A screen's own page (#rotation/<name>) and a built-in app's (#builtins/<key>): the
// picture, where it shows, and every setting, with a breadcrumb back to the list.

import { appName, t } from "../i18n.js";
import { liveCheck } from "../livecheck.js";
import { placementOf, secondsOf, setPlacement, setSeconds } from "../placement.js";
import { setFocus, store } from "../store.js";
import { appIcon, h, icon, panel, row, section, segmented, slider } from "../ui.js";
import { appSettings } from "./builtin-settings.js";
import { page, thumb } from "./common.js";
import { screenOptions } from "./screen-options.js";

const CONNECTED = { home: "homeassistant", agenda: "calendar" };

export function breadcrumb(parentId, current) {
  return h("nav", { class: "breadcrumb", "aria-label": t("ui.breadcrumb") },
    h("a", { href: `#${parentId}` }, t(`page.${parentId}`)), icon("chevron-right"), h("span", { "aria-current": "page" }, current));
}

function head(key, description) {
  return h("div", { class: "page-head detail-head" },
    h("div", {}, h("h1", {}, appIcon(key, "lg"), appName(key)), description && h("p", {}, description)));
}

function placementPanel(kind, key) {
  const p = placementOf(kind, key);
  const { min, max } = store.state.slotSeconds;
  const choices = ["off", "kept", "rotate", "pin"].map((v) => [v, t(`place.${v}`)]);
  return panel(
    row(t("place.title"), p === "rotate" && store.draft.rotation.mode === "single" ? t("place.pausedHint") : t(`place.${p}Hint`),
      segmented(choices, p, (v) => setPlacement(kind, key, v), t("place.title")),
      { icon: p === "pin" ? "pin" : "repeat", path: kind === "screen" ? "screens.enabled" : "device.keep_builtins" }),
    p === "rotate" ? row(t("place.seconds"), null,
      slider(min, Math.min(max, 120), secondsOf(kind, key), (v) => setSeconds(kind, key, v), t("place.seconds")),
      { icon: "timer", path: "rotation.slots" }) : null,
  );
}

export function screenPage(name) {
  setFocus({ type: "screen", key: name });
  const saved = store.saved.screen?.[name] ?? {};
  const draft = store.draft.screen?.[name] ?? {};
  const unsaved = JSON.stringify(saved) !== JSON.stringify(draft);
  const options = screenOptions(name);
  const connection = CONNECTED[name];
  return page(
    breadcrumb("rotation", appName(name)),
    head(name, t(`screen.${name}`)),
    liveCheck(name, unsaved ? draft : null, { unsaved }),
    section(t("place.title")), placementPanel("screen", name),
    options ? section(t("library.options")) : null,
    options ? panel(...options) : null,
    connection ? h("p", { class: "muted detail-note" }, icon("link"), t(`conn.${connection}Hint`), " ",
      h("a", { class: "link", href: "#connections" }, `${t("page.connections")} →`)) : null,
  );
}

export function appPage(key) {
  setFocus({ type: "builtin", key });
  const live = store.state.clock.builtins?.[key];
  const settings = appSettings(key);
  const state = live ? (live.enabled ? t("builtins.onNow") : t("builtins.offNow")) : null;
  return page(
    breadcrumb("builtins", appName(key)),
    head(key, [state, live?.credentials ? t("builtins.linked") : null].filter(Boolean).join(" · ")),
    h("figure", { class: "detail-figure" }, thumb(key, false),
      h("figcaption", { class: "muted" }, t("preview.approx"))),
    section(t("place.title")), placementPanel("builtin", key),
    settings.length ? section(t("builtins.settings")) : null,
    settings.length ? panel(...settings) : null,
  );
}
