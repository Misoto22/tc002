// tc002 UI shell: chrome (sidebar, top bar, save bar), routing, shortcuts.

import { t } from "./i18n.js";
import { commands, openPalette } from "./palette.js";
import { applyPrefs, prefs, setPref } from "./prefs.js";
import { startPreview } from "./preview.js";
import * as store from "./store.js";
import { h, icon, menu, transition } from "./ui.js";
import { apps } from "./pages/apps.js";
import { builtins } from "./pages/builtins.js";
import { display } from "./pages/display.js";
import { integrations } from "./pages/integrations.js";
import { messages } from "./pages/messages.js";
import { overview } from "./pages/overview.js";
import { playlist } from "./pages/playlist.js";

const PAGES = [
  ["overview", overview, "layout-dashboard", "nav.clock"],
  ["playlist", playlist, "list-video", "nav.clock"],
  ["builtins", builtins, "blocks", "nav.clock"],
  ["display", display, "sun", "nav.clock"],
  ["apps", apps, "sliders-horizontal", "nav.clock"],
  ["messages", messages, "message-square-text", "nav.send"],
  ["integrations", integrations, "plug", "nav.system"],
];
const $ = (id) => document.getElementById(id);
const current = () => (PAGES.some(([id]) => id === location.hash.slice(1)) ? location.hash.slice(1) : "overview");

// ---- chrome -----------------------------------------------------------------------

function renderNav() {
  const s = store.store;
  let group = null;
  $("nav").replaceChildren(...PAGES.flatMap(([id, , ico, grp]) => {
    const els = [];
    if (grp !== group) { group = grp; els.push(h("div", { class: "nav-label" }, t(grp))); }
    els.push(h("a", { class: "nav-item", href: `#${id}`, "aria-current": current() === id ? "page" : undefined },
      icon(ico), h("span", {}, t(`page.${id}`)),
      id === "playlist" && s.draft ? h("span", { class: "count" }, s.draft.playlist.slots.length) : null));
    return els;
  }));
  const clock = s.state?.clock;
  $("brand-sub").replaceChildren(h("span", { class: `dot ${clock?.online ? "ok" : "bad"}` }),
    clock ? (clock.online ? `${clock.host} · ${clock.base.appVer}` : t("badge.offline")) : "…");
  $("config-path").textContent = s.state?.config.path ?? "";
}

function renderTopbar() {
  const status = store.statusOf();
  $("crumb").replaceChildren(t(`page.${current()}`));
  const pill = $("status");
  pill.className = `status-pill ${status.kind}`;
  pill.replaceChildren(icon(status.icon, `icon${status.icon === "loader-circle" ? " spin" : ""}`), h("span", {}, status.text));
  pill.title = store.store.op?.detail ?? "";
  $("theme").replaceChildren(icon({ system: "monitor", light: "sun", dark: "moon" }[prefs.theme]));
  $("theme").title = t("ui.theme");
  $("lang").textContent = prefs.lang === "zh" ? "中" : "EN";
  $("lang").title = t("ui.language");
  $("palette-btn").title = t("ui.search");
}

function renderSavebar() {
  const n = store.dirtyPaths().length;
  const bar = $("savebar");
  bar.hidden = n === 0;
  $("savebar-text").textContent = `${t("save.unsaved")} · ${n}`;
  $("discard").textContent = t("save.discard");
  $("save").replaceChildren(icon("save"), t("save.save"));
  $("save").disabled = store.store.op?.kind === "saving";
}

// Mark rows whose tc002.toml value differs from what is saved.
function markDirty() {
  const dirty = store.dirtyPaths();
  for (const el of document.querySelectorAll("#main [data-path]")) {
    const p = el.dataset.path;
    el.classList.toggle("dirty", dirty.some((d) => d === p || d.startsWith(`${p}.`) || p.startsWith(`${d}.`)));
  }
}

function render() {
  if (!store.store.state) return;
  $("main").replaceChildren(PAGES.find(([id]) => id === current())[1]());
  renderNav();
  renderTopbar();
  renderSavebar();
  markDirty();
}

function go(id) {
  if (current() !== id) location.hash = id; // hashchange renders, with a transition
}

function openActivity() {
  const log = store.store.log;
  const anchor = $("status");
  menu(anchor, [[t("activity.title"), log.map((e, i) => [i,
    `${e.at.toLocaleTimeString()} · ${t(e.action)} — ${e.detail ?? ""}`, e.ok ? "circle-check" : "circle-alert"])]],
  () => {}, t("activity.empty"));
}

function palette() {
  openPalette(commands({
    pages: PAGES, go, store: store.store, setPref: (k, v) => setPref(k, v, render),
    actions: {
      dirtyCount: () => store.dirtyPaths().length, save: () => store.save(), discard: store.discard,
      applySaved: store.applySaved, setLive: store.setLive, send: store.send, show: store.show,
      refresh: store.load, openActivity,
    },
  }));
}

// ---- wiring -------------------------------------------------------------------------

applyPrefs();
store.subscribe((what) => {
  if (what === "render") render();
  else { renderTopbar(); renderSavebar(); renderNav(); markDirty(); }
});
window.addEventListener("hashchange", () => transition(() => { render(); $("main").scrollTop = 0; }));
$("save").addEventListener("click", () => store.save());
$("discard").addEventListener("click", store.discard);
$("status").addEventListener("click", openActivity);
$("palette-btn").addEventListener("click", palette);
$("theme").addEventListener("click", (e) => menu(e.currentTarget, [[t("ui.theme"), [
  ["system", t("pal.themeSystem"), "monitor"], ["light", t("pal.themeLight"), "sun"], ["dark", t("pal.themeDark"), "moon"],
]]], (v) => setPref("theme", v, render)));
$("lang").addEventListener("click", () => setPref("lang", prefs.lang === "zh" ? "en" : "zh", render));
document.addEventListener("keydown", (e) => {
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); palette(); }
  if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); if (store.dirtyPaths().length) store.save(); }
});
window.addEventListener("beforeunload", (e) => { if (store.dirtyPaths().length) e.preventDefault(); });

renderTopbar();
store.load()
  .then(() => startPreview($("preview")))
  .catch((err) => $("main").replaceChildren(h("div", { class: "page" }, h("div", { class: "empty" }, t("err.load", { msg: err.message })))));
