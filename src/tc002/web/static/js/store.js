// Application state and every action that talks to the server.
//
// state  — server truth from /api/state (clock, integrations, schema)
// saved  — tc002.toml as last loaded;  draft — tc002.toml being edited
// status — what the user should know right now (see statusOf)
// live   — whether the draft is playing on the hardware before saving

import { get, post, postOnExit } from "./api.js";
import { appName, t } from "./i18n.js";
import { toast } from "./ui.js";
import { TIMING } from "./timing.js";

export const store = {
  state: null, saved: null, draft: null,
  focus: { type: "rotation" }, // what the preview panel shows
  op: null, // { kind: "saving" | "applied" | "offline" | "error", at, detail }
  live: { on: false, pending: false },
  log: [],
};

const subscribers = new Set();
export const subscribe = (fn) => subscribers.add(fn);
const notify = (what) => { for (const fn of subscribers) fn(what); };

const clone = (v) => structuredClone(v);
const normalise = (d) => ({ ...d, display: d.display ?? {}, apps: d.apps ?? {} });

// Changed leaf paths between two tc002.toml documents; arrays compare as one value.
export function diffPaths(a, b, prefix = "") {
  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);
  // a table that exists on one side only compares field by field against an empty one
  if (a === undefined && isObj(b)) a = {};
  if (b === undefined && isObj(a)) b = {};
  if (!isObj(a) || !isObj(b)) {
    return JSON.stringify(a) === JSON.stringify(b) ? [] : [prefix];
  }
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  return [...keys].flatMap((k) => diffPaths(a[k], b[k], prefix ? `${prefix}.${k}` : k));
}

export const dirtyPaths = () => (store.draft ? diffPaths(store.saved, store.draft) : []);

export function statusOf() {
  if (!store.state) return { kind: "loading", text: t("status.loading"), icon: "loader-circle" };
  if (store.op?.kind === "saving") return { kind: "busy", text: t("status.saving"), icon: "loader-circle" };
  if (store.live.pending) return { kind: "busy", text: t("status.liveStarting"), icon: "loader-circle" };
  if (store.live.on) return { kind: "live", text: t("status.live"), icon: "radio" };
  const n = dirtyPaths().length;
  if (n) return { kind: "dirty", text: t("status.dirty", { n }), icon: "circle-alert" };
  const recent = store.op && Date.now() - store.op.at < TIMING.statusSettleMs;
  if (recent && store.op.kind === "applied") return { kind: "ok", text: t("status.applied"), icon: "circle-check" };
  if (store.op?.kind === "offline") return { kind: "warn", text: t("status.savedOffline"), icon: "cloud-off" };
  if (store.op?.kind === "error") return { kind: "error", text: t("status.error"), icon: "circle-alert" };
  if (store.state.clock.drift?.length) return { kind: "warn", text: t("status.drift"), icon: "triangle-alert" };
  return { kind: "ok", text: t("status.synced"), icon: "check" };
}

function record(action, ok, detail) {
  store.log.unshift({ at: new Date(), action, ok, detail });
  store.log.length = Math.min(store.log.length, 30);
}

function changesText(changes) {
  return changes.length ? t("activity.changes", { n: changes.length }) : t("activity.noChanges");
}

// ---- loading and editing --------------------------------------------------------

export async function load() {
  const keepDraft = store.draft && dirtyPaths().length;
  store.state = await get("/api/state");
  store.saved = normalise(store.state.config.data);
  if (!keepDraft) store.draft = clone(store.saved);
  notify("render");
}

export function edit(mutate, { rerender = false } = {}) {
  mutate(store.draft);
  notify(rerender ? "render" : "draft");
  if (store.live.on) scheduleLive();
}

export function setFocus(focus) {
  if (JSON.stringify(focus) === JSON.stringify(store.focus)) return;
  store.focus = focus;
  notify("focus");
  if (store.live.on) scheduleLive();
}

export function discard() {
  store.draft = clone(store.saved);
  notify("render");
  if (store.live.on) setLive(false);
}

// ---- save & apply ---------------------------------------------------------------

export async function save(data = store.draft) {
  store.op = { kind: "saving", at: Date.now() };
  notify("status");
  try {
    const result = await post("/api/config", data);
    store.op = { kind: result.error ? "offline" : "applied", at: Date.now(), detail: result.error };
    record("activity.save", !result.error, result.error ?? changesText(result.changes));
    if (result.error) toast(t("save.saved"), result.error, "warn");
    else toast(t("save.savedApplied"), changesText(result.changes) + (result.serviceRestarted ? ` · ${t("save.serviceReloaded")}` : ""));
    store.draft = null;
    if (store.live.on) await stopLive(false);
    await load();
    setTimeout(() => notify("status"), TIMING.statusSettleMs + 100); // "Applied" settles to "In sync"
  } catch (err) {
    store.op = { kind: "error", at: Date.now(), detail: err.message };
    record("activity.save", false, err.message);
    toast(err.title ?? t("status.error"), err.message, "error");
    notify("status");
  }
}

export const applySaved = () => save(store.saved);

// ---- live preview on the hardware -----------------------------------------------

let liveTimer;
let heartbeat;

function focusTarget() {
  const f = store.focus;
  if (f.type === "builtin" && store.draft.device.keep_builtins.includes(f.key)) return { builtin: f.key };
  if (f.type === "screen") return { screen: f.key };
  return null;
}

function scheduleLive() {
  clearTimeout(liveTimer);
  liveTimer = setTimeout(pushLive, TIMING.liveDebounceMs);
}

async function pushLive() {
  store.live.pending = true;
  notify("status");
  try {
    const result = await post("/api/live", { data: store.draft, focus: focusTarget() });
    store.live.heldFor = result.heldFor;
    if (result.changes.length) record("activity.live", true, result.changes.slice(0, 4).join(" · "));
  } catch (err) {
    toast(err.title ?? t("activity.live"), err.message, "error");
    record("activity.live", false, err.message);
    store.live.on = false;
    clearInterval(heartbeat);
  } finally {
    store.live.pending = false;
    notify("status");
  }
}

export async function setLive(on) {
  if (on === store.live.on) return;
  store.live.on = on;
  notify("status");
  if (on) {
    await pushLive();
    // renew the server's rotation hold at half its length, so it never lapses while live
    if (store.live.on && store.live.heldFor) heartbeat = setInterval(pushLive, (store.live.heldFor * 1000) / 2);
  } else {
    await stopLive(true);
  }
}

async function stopLive(log) {
  clearTimeout(liveTimer);
  clearInterval(heartbeat);
  store.live.on = false;
  try {
    const result = await post("/api/live/stop", {});
    if (log) record("activity.liveStop", true, changesText(result.changes));
  } catch (err) {
    toast(err.title, err.message, "error");
  }
  notify("status");
}

window.addEventListener("pagehide", () => { if (store.live.on) postOnExit("/api/live/stop", {}); });

// ---- one-off actions ------------------------------------------------------------

export async function show(target) {
  const label = appName(target.screen ?? target.builtin);
  try {
    await post("/api/show", target);
    record("activity.show", true, label);
    toast(t("activity.show"), label);
  } catch (err) {
    record("activity.show", false, err.message);
    toast(err.title, err.message, "error");
  }
  notify("status");
}

export async function send(message) {
  try {
    const r = await post("/api/message", message);
    record("activity.message", true, message.text);
    toast(t("msg.sent"), t("msg.plays", { s: r.seconds }));
  } catch (err) {
    record("activity.message", false, err.message);
    toast(err.title, err.message, "error");
  }
  notify("status");
}

// ---- quick settings and presets -------------------------------------------------

let quickTimer;
let quickPatch = {};

// Brightness, volume…: written to tc002.toml and applied at once, without touching an
// unsaved draft. Calls within 200 ms are merged so a dragged slider sends one request.
export function quick(display) {
  quickPatch = { ...quickPatch, ...display };
  for (const target of [store.saved, store.draft]) target.display = { ...target.display, ...display };
  notify("status");
  clearTimeout(quickTimer);
  quickTimer = setTimeout(async () => {
    const patch = quickPatch;
    quickPatch = {};
    try {
      const r = await post("/api/quick", { display: patch });
      store.op = { kind: r.error ? "offline" : "applied", at: Date.now(), detail: r.error };
      record("quick.title", !r.error, r.error ?? changesText(r.changes));
    } catch (err) {
      store.op = { kind: "error", at: Date.now(), detail: err.message };
      toast(err.title, err.message, "error");
    }
    notify("status");
    setTimeout(() => notify("status"), TIMING.statusSettleMs + 100);
  }, TIMING.quickDebounceMs);
}

export async function applyPreset(id) {
  const { data } = await post("/api/preset", { data: store.draft, preset: id });
  store.draft = { ...data, display: data.display ?? {}, apps: data.apps ?? {} };
  toast(t("preset.loaded"), t("preset.loadedHint"));
  notify("render");
  if (store.live.on) scheduleLive();
}
