// Where a screen or a built-in app shows: off, in the rotation (for how long), only it,
// or kept on the clock without a turn. One answer instead of a switch here and a list
// somewhere else, so turning something on says straight away where it will appear.

import { t } from "./i18n.js";
import { edit, store } from "./store.js";
import { h, icon, menu } from "./ui.js";

export const DEFAULT_SECONDS = 15;
const field = (kind) => (kind === "screen" ? "screen" : "builtin");
const owned = (d, kind) => (kind === "screen" ? d.screens.enabled : d.device.keep_builtins);
const matches = (kind, key) => (s) => s?.[field(kind)] === key;

// "off" | "rotate" | "pin" | "kept"
export function placementOf(kind, key, d = store.draft) {
  if (!owned(d, kind).includes(key)) return "off";
  if (d.rotation.mode === "single" && matches(kind, key)(d.rotation.show)) return "pin";
  return d.rotation.slots.some(matches(kind, key)) ? "rotate" : "kept";
}

export const secondsOf = (kind, key, d = store.draft) =>
  d.rotation.slots.find(matches(kind, key))?.seconds ?? DEFAULT_SECONDS;

function turnOn(dr, kind, key) {
  const list = owned(dr, kind);
  if (!list.includes(key)) list.push(key);
}

function unpin(dr, kind, key) {
  if (!matches(kind, key)(dr.rotation.show)) return;
  delete dr.rotation.show;
  delete dr.rotation.mode;
}

export function setPlacement(kind, key, target) {
  edit((dr) => {
    const slot = { [field(kind)]: key };
    if (target === "off") {
      if (kind === "screen") dr.screens.enabled = dr.screens.enabled.filter((x) => x !== key);
      else dr.device.keep_builtins = dr.device.keep_builtins.filter((x) => x !== key);
      dr.rotation.slots = dr.rotation.slots.filter((s) => !matches(kind, key)(s));
      unpin(dr, kind, key);
      return;
    }
    turnOn(dr, kind, key);
    if (target === "pin") {
      dr.rotation.mode = "single";
      dr.rotation.show = slot;
      return;
    }
    unpin(dr, kind, key);
    if (target === "kept") dr.rotation.slots = dr.rotation.slots.filter((s) => !matches(kind, key)(s));
    if (target === "rotate" && !dr.rotation.slots.some(matches(kind, key))) {
      dr.rotation.slots.push({ ...slot, seconds: DEFAULT_SECONDS });
    }
  }, { rerender: true });
}

export function setSeconds(kind, key, seconds) {
  edit((dr) => {
    const slot = dr.rotation.slots.find(matches(kind, key));
    if (slot) slot.seconds = seconds;
  });
}

export function placementLabel(kind, key) {
  const p = placementOf(kind, key);
  if (p === "rotate" && store.draft.rotation.mode === "single") return t("place.badgePaused");
  if (p === "rotate") return t("place.badgeRotate", { s: secondsOf(kind, key) });
  if (p === "pin") return t("place.badgePin");
  if (p === "kept") return t("place.badgeKept");
  return t("place.badgeOff");
}

// A compact button in a list row: what it does now, and a menu to change it.
export function placementButton(kind, key, href) {
  const p = placementOf(kind, key);
  return h("button", {
    type: "button", class: `place-btn place-${p}`, "aria-haspopup": "menu",
    onClick: (e) => {
      e.stopPropagation(); // the row around it opens the item's page
      menu(e.currentTarget, [[t("place.title"), [
        ["off", t("place.off"), "power", null, { current: p === "off" }],
        ["kept", t("place.kept"), "layers", null, { current: p === "kept" }],
        ["rotate", t("place.rotate"), "repeat", null, { current: p === "rotate" }],
        ["pin", t("place.pin"), "pin", null, { current: p === "pin" }],
      ]], ["", [["settings", t("place.settings"), "sliders-horizontal"]]]],
      (v) => { if (v === "settings") location.hash = href; else setPlacement(kind, key, v); });
    },
  }, h("span", { class: "place-dot" }), placementLabel(kind, key), icon("chevron-down"));
}
