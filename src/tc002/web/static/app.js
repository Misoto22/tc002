// tc002 UI shell: loads state, keeps the tc002.toml draft, routes between pages, saves.

import { h, icon, toast } from "./ui.js";
import * as views from "./views.js";

const TOKEN = document.querySelector('meta[name="tc002-token"]').content;
const PAGES = [
  ["Clock", [["overview", "Overview", "overview"], ["playlist", "Playlist", "playlist"],
    ["builtins", "Built-in apps", "apps"], ["display", "Display", "display"],
    ["appSettings", "App settings", "settings"]]],
  ["Send", [["messages", "Messages", "message"]]],
  ["System", [["integrations", "Integrations", "plug"]]],
];

const ctx = {
  state: null,
  saved: null, // tc002.toml as last loaded
  draft: null, // tc002.toml being edited
  message: { type: "text", text: "", color: "green", kind: "done" },
  edit(mutate, rerender = false) {
    mutate(ctx.draft);
    updateSavebar();
    if (rerender) render();
  },
  refresh: () => load(),
  applySaved: () => save(ctx.saved),
  show: (slot) => post("/api/show", slot).then(() => toast(`Showing ${slot.screen ?? slot.builtin}`)),
  send: (msg) => post("/api/message", msg).then((r) => toast("Sent to the clock", `Plays for about ${r.seconds}s, then clears`)),
};

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-TC002-Token": TOKEN, ...options.headers },
  });
  const body = await res.json();
  if (!res.ok) {
    const detail = [body.detail, ...(body.errors ?? []).map((e) => e.message)].filter(Boolean).join(" · ");
    toast(body.title ?? "Request failed", detail, "error");
    throw new Error(detail);
  }
  return body;
}

const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body) });

const clone = (v) => structuredClone(v);
const dirty = () => JSON.stringify(ctx.draft) !== JSON.stringify(ctx.saved);

function normalise(data) {
  return { ...data, display: data.display ?? {}, apps: data.apps ?? {} };
}

async function load() {
  const keepDraft = ctx.draft && dirty();
  ctx.state = await request("/api/state");
  ctx.saved = normalise(ctx.state.config.data);
  if (!keepDraft) ctx.draft = clone(ctx.saved);
  renderChrome();
  render();
}

async function save(data = ctx.draft) {
  const button = document.getElementById("save");
  button.disabled = true;
  try {
    const result = await post("/api/config", data);
    const n = result.changes.length;
    if (result.error) toast("Saved to tc002.toml", result.error, "error");
    else toast("Saved and applied", n ? `${n} change${n > 1 ? "s" : ""} on the clock` +
      (result.serviceRestarted ? " · service reloaded" : "") : "The clock already matched");
    ctx.draft = null;
    await load();
  } finally {
    button.disabled = false;
    updateSavebar();
  }
}

function updateSavebar() {
  document.getElementById("savebar").hidden = !dirty();
}

function current() {
  const page = location.hash.slice(1);
  return PAGES.flatMap(([, items]) => items).some(([id]) => id === page) ? page : "overview";
}

function renderChrome() {
  const { clock, config } = ctx.state;
  document.getElementById("brand-sub").textContent = clock.online
    ? `${clock.host} · ${clock.base.appVer}` : "offline";
  document.getElementById("config-path").textContent = config.path ?? "no tc002.toml";
  const nav = document.getElementById("nav");
  nav.replaceChildren(...PAGES.flatMap(([label, items]) => [
    h("div", { class: "nav-label" }, label),
    ...items.map(([id, text, ico]) => h("a", {
      class: "nav-item", href: `#${id}`, "aria-current": current() === id ? "page" : undefined,
    }, icon(ico), text,
    id === "playlist" ? h("span", { class: "count" }, ctx.draft.playlist.slots.length) : null)),
  ]));
}

function render() {
  const main = document.getElementById("main");
  const scroll = main.scrollTop;
  main.replaceChildren(views[current()](ctx));
  main.scrollTop = scroll;
  for (const a of document.querySelectorAll(".nav-item")) {
    a.toggleAttribute("aria-current", a.getAttribute("href") === `#${current()}`);
    if (a.hasAttribute("aria-current")) a.setAttribute("aria-current", "page");
  }
}

window.addEventListener("hashchange", () => { render(); document.getElementById("main").scrollTop = 0; });
document.getElementById("save").addEventListener("click", () => save());
document.getElementById("discard").addEventListener("click", () => { ctx.draft = clone(ctx.saved); updateSavebar(); render(); });
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "s") {
    e.preventDefault();
    if (dirty()) save();
  }
});
window.addEventListener("beforeunload", (e) => { if (ctx.draft && dirty()) e.preventDefault(); });

load().catch((err) => {
  document.getElementById("main").replaceChildren(
    h("div", { class: "page" }, h("div", { class: "empty" }, `Could not load: ${err.message}`)));
});
