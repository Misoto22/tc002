// tc002 UI shell: chrome (sidebar, top bar, save bar), routing, shortcuts.

import { loadAssets } from "./assets.js";
import { t } from "./i18n.js";
import { commands, openPalette } from "./palette.js";
import { PALETTES, applyPrefs, prefs, setPref } from "./prefs.js";
import { startPreview } from "./preview.js";
import { openQuick } from "./quick.js";
import * as store from "./store.js";
import { h, icon, menu, transition } from "./ui.js";
import { builtins } from "./pages/builtins.js";
import { display } from "./pages/display.js";
import { integrations } from "./pages/integrations.js";
import { messages } from "./pages/messages.js";
import { overview } from "./pages/overview.js";
import { rotation } from "./pages/rotation.js";
import { setup } from "./pages/setup.js";
import { play } from "./pages/play.js";
import { connections } from "./pages/connections.js";
import { pollAgents } from "./agents.js";
import { followUiPalette } from "./appearance.js";

// [id, page, icon, nav group]; a page without a group (setup) is reached from the first
// run and from the overview, not from the sidebar.
const PAGES = [
  ["overview", overview, "layout-dashboard", "nav.clock"],
  ["rotation", rotation, "repeat", "nav.clock"],
  ["builtins", builtins, "blocks", "nav.clock"],
  ["display", display, "sun", "nav.clock"],
  ["messages", messages, "message-square-text", "nav.send"],
  ["play", play, "gamepad-2", "nav.send"],
  ["integrations", integrations, "plug", "nav.system"],
  ["connections", connections, "link", "nav.system"],
  ["setup", setup, "wand-sparkles", null],
];
const ALIASES = { apps: "builtins", sessions: "overview" }; // pages merged away, for old links
const $ = (id) => document.getElementById(id);
function current() {
  const id = location.hash.slice(1);
  const known = ALIASES[id] ?? id;
  return PAGES.some(([p]) => p === known) ? known : "overview";
}

// ---- chrome -----------------------------------------------------------------------

function navCount(id) {
  const d = store.store.draft;
  if (id !== "rotation" || !d) return null;
  if (d.rotation.mode === "single") return h("span", { class: "count" }, icon("pin"));
  return h("span", { class: "count" }, d.rotation.slots.length);
}

// One pill behind the nav that slides to the current page instead of jumping.
const indicator = h("span", { class: "nav-indicator", "aria-hidden": "true", hidden: true });
function moveIndicator() {
  const nav = $("nav");
  const item = nav.querySelector('.nav-item[aria-current="page"]');
  nav.append(indicator);
  if (!item) { indicator.hidden = true; return; }
  const first = indicator.hidden || !indicator.style.transform; // appear in place, then slide
  indicator.hidden = false;
  if (first) indicator.style.transition = "none";
  indicator.style.transform = `translateY(${item.offsetTop}px)`;
  indicator.style.height = `${item.offsetHeight}px`;
  if (first) requestAnimationFrame(() => { indicator.style.transition = ""; });
}

function renderNav() {
  const s = store.store;
  const groups = Map.groupBy(PAGES.filter(([, , , grp]) => grp), ([, , , grp]) => grp);
  $("nav").replaceChildren(...[...groups].map(([grp, pages]) => h("div", { class: "nav-group" },
    h("div", { class: "nav-label" }, t(grp)),
    ...pages.map(([id, , ico]) => h("a", {
      class: "nav-item", href: `#${id}`, title: t(`page.${id}`),
      "aria-current": current() === id ? "page" : undefined,
    }, icon(ico), h("span", {}, t(`page.${id}`)),
    navCount(id))))));
  moveIndicator();
  const clock = s.state?.clock;
  $("brand-sub").replaceChildren(h("span", { class: `dot ${clock?.online ? "ok" : "bad"}` }),
    clock ? (clock.online ? `${clock.host} · ${clock.base.appVer}` : t("badge.offline")) : "…");
  $("config-path").textContent = s.state?.config.shown ?? "";
  $("config-path").title = s.state?.config.path ?? "";
  renderQuickButton();
}

// Brightness and volume, at the foot of the sidebar: the label says what it is, so it is
// not mistaken for the light/dark switch in the top bar.
function renderQuickButton() {
  const btn = $("quick");
  const online = store.store.state?.clock.online;
  btn.disabled = !online;
  btn.title = online ? t("quick.open") : t("badge.offline");
  btn.replaceChildren(icon("sliders-horizontal"), h("span", {}, t("quick.open")));
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
  $("collapse").title = prefs.sidebar === "collapsed" ? t("nav.expand") : t("nav.collapse");
  document.querySelector(".app").classList.toggle("collapsed", prefs.sidebar === "collapsed");
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
  for (const el of document.querySelectorAll("#page [data-path]")) {
    const p = el.dataset.path;
    el.classList.toggle("dirty", dirty.some((d) => d === p || d.startsWith(`${p}.`) || p.startsWith(`${d}.`)));
  }
}

// `entering`: a page the user went to animates in; anything else (reload, edit, save)
// redraws in place, so nothing on screen slides about.
let firstPaint = true; // the first page after start-up animates in too
function render(entering = false) {
  if (!store.store.state) return;
  if (entering || firstPaint) delete document.documentElement.dataset.refresh;
  else document.documentElement.dataset.refresh = "";
  firstPaint = false;
  $("page").replaceChildren(PAGES.find(([id]) => id === current())[1]());
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
window.addEventListener("hashchange", () => transition(() => { render(true); $("main").scrollTop = 0; }));
window.addEventListener("hashchange", () => document.querySelectorAll(".popover, .menu").forEach((p) => p.remove()));
$("save").addEventListener("click", () => store.save());
$("discard").addEventListener("click", store.discard);
$("status").addEventListener("click", openActivity);
$("palette-btn").addEventListener("click", palette);
function openTheme(anchor) {
  const box = anchor.getBoundingClientRect();
  const origin = { x: box.left + box.width / 2, y: box.top + box.height / 2 };
  const mode = (id, label, ico) => [`theme:${id}`, label, ico, null, { current: prefs.theme === id }];
  const colour = (id) => [`palette:${id}`, t(`palette.${id}`), null, null, { swatch: id, current: prefs.palette === id }];
  menu(anchor, [
    [t("ui.theme"), [mode("system", t("pal.themeSystem"), "monitor"), mode("light", t("pal.themeLight"), "sun"),
      mode("dark", t("pal.themeDark"), "moon")]],
    [t("ui.palette"), PALETTES.map(colour)],
  ], (v) => {
    const [key, value] = v.split(":");
    setPref(key, value, render, origin);
    if (key === "palette") followUiPalette(value);
  });
}
$("theme").addEventListener("click", (e) => openTheme(e.currentTarget));
$("lang").addEventListener("click", () => setPref("lang", prefs.lang === "zh" ? "en" : "zh", render));
$("quick").addEventListener("click", (e) => openQuick(e.currentTarget));
const toggleSidebar = () => setPref("sidebar", prefs.sidebar === "collapsed" ? "open" : "collapsed", renderTopbar);
$("collapse").addEventListener("click", toggleSidebar);
document.addEventListener("keydown", (e) => {
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); palette(); }
  if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); if (store.dirtyPaths().length) store.save(); }
  const typing = e.target instanceof Element && e.target.closest("input, select, textarea, [contenteditable]");
  if (e.key === "[" && !mod && !typing) { e.preventDefault(); toggleSidebar(); } // as in Linear
});
window.addEventListener("beforeunload", (e) => { if (store.dirtyPaths().length) e.preventDefault(); });

renderTopbar();
// A refresh redraws in place: no entrance animations, only changed numbers count.
pollAgents(() => renderNav()); // live screen previews follow agent state
loadAssets() // icons and LED data first: pages draw with them
  .then(store.load)
  .then(() => { if (!store.store.state.clock.host && current() === "overview") go("setup"); })
  .then(() => startPreview($("device")))
  .catch((err) => $("page").replaceChildren(h("div", { class: "page" }, h("div", { class: "empty" }, t("err.load", { msg: err.message })))));
