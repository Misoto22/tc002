// The preview panel: what the clock would show with the current draft, and the switch that
// plays the draft on the real hardware before saving.

import { appName, t } from "./i18n.js";
import { draw, loadFont } from "./led.js";
import { simulate } from "./sims.js";
import { setLive, store, subscribe } from "./store.js";
import { h, icon, toggle } from "./ui.js";

const SCREEN_GIF = { claude: "claude-busy", sys: "sys" };
let root;
let canvas;
let img;
let caption;
let chips;
let liveRow;
let playing = true;
let cycle = { index: 0, started: performance.now() };
let lastSource = "";

function merged() {
  const clock = store.state?.clock ?? {};
  const settings = { ...clock.settings, ...store.draft.display };
  const apps = structuredClone(clock.apps ?? {});
  for (const [app, fields] of Object.entries(store.draft.apps)) {
    apps[app] = { ...apps[app], ...fields };
    if (fields.displayInfo) apps[app].displayInfo = { ...clock.apps?.[app]?.displayInfo, ...fields.displayInfo };
  }
  return { settings, apps };
}

function brightness(settings) {
  const b = settings.brightness ?? {};
  const pct = b[b.level ?? "high"] ?? 100;
  return 0.25 + 0.75 * (pct / 100);
}

// What to draw now: { kind: "sim", key } or { kind: "gif", src }.
function source() {
  const f = store.focus;
  if (f.type === "message") return { kind: "gif", src: f.src, label: t("preview.message") };
  if (f.type === "screen") return { kind: "gif", src: `/api/preview/${SCREEN_GIF[f.key] ?? f.key}.gif`, label: appName(f.key) };
  if (f.type === "builtin") return { kind: "sim", key: f.key, label: appName(f.key) };
  const slots = store.draft.playlist.slots;
  if (!slots.length) return { kind: "sim", key: "clock", label: appName("clock") };
  const slot = slots[cycle.index % slots.length];
  return slot.screen
    ? { kind: "gif", src: `/api/preview/${SCREEN_GIF[slot.screen] ?? slot.screen}.gif`, label: appName(slot.screen) }
    : { kind: "sim", key: slot.builtin, label: appName(slot.builtin) };
}

function tick() {
  if (!store.draft || !root.isConnected) return;
  const slots = store.draft.playlist.slots;
  const now = performance.now();
  if (store.focus.type === "playlist" && slots.length) {
    const slot = slots[cycle.index % slots.length];
    if (!playing) cycle.started = now - (cycle.paused ?? 0);
    else if (now - cycle.started >= slot.seconds * 1000) cycle = { index: (cycle.index + 1) % slots.length, started: now };
    cycle.paused = now - cycle.started;
    updateChips(slots, (now - cycle.started) / (slot.seconds * 1000));
  }
  const src = source();
  const { settings, apps } = merged();
  root.querySelector(".stage").style.filter = `brightness(${brightness(settings).toFixed(2)})`;
  const key = JSON.stringify(src);
  if (key !== lastSource) { // cross-fade between sources
    lastSource = key;
    root.querySelector(".stage").animate([{ opacity: 0.2 }, { opacity: 1 }], { duration: 220, easing: "ease-out" });
    caption.replaceChildren(src.label, src.kind === "sim" ? h("span", { class: "muted" }, ` · ${t("preview.approx")}${src.key === "weather" ? `, ${t("preview.sample")}` : ""}`) : "");
  }
  if (src.kind === "gif") {
    canvas.hidden = true;
    img.hidden = false;
    if (img.getAttribute("src") !== src.src) img.src = src.src;
  } else {
    img.hidden = true;
    canvas.hidden = false;
    draw(canvas, simulate(src.key, settings, apps, Date.now()));
  }
}

function updateChips(slots, progress) {
  if (chips.childElementCount !== slots.length) renderChips();
  [...chips.children].forEach((chip, i) => {
    chip.classList.toggle("current", i === cycle.index % slots.length);
    chip.style.setProperty("--p", i === cycle.index % slots.length ? Math.min(1, progress).toFixed(3) : 0);
  });
}

function renderChips() {
  const slots = store.draft.playlist.slots;
  chips.replaceChildren(...slots.map((s, i) => h("button", {
    class: "chip", type: "button",
    onClick: () => { cycle = { index: i, started: performance.now() }; },
  }, appName(s.screen ?? s.builtin))));
}

function renderLive() {
  const online = store.state?.clock.online;
  liveRow.replaceChildren(
    h("div", { class: "row-text" },
      h("div", { class: "row-title" }, store.live.on ? h("span", { class: "live-dot" }) : null, t("preview.live")),
      h("div", { class: "row-hint" }, !online ? t("preview.offline") : store.live.on ? t("preview.liveOn") : t("preview.liveHint"))),
    toggle(store.live.on, (on) => setLive(on), { label: t("preview.live"), disabled: !online }));
}

export function mountPreview(container) {
  canvas = h("canvas", { width: 520, height: 160, class: "led-canvas", "aria-label": t("preview.title") });
  img = h("img", { class: "led-img", alt: "", hidden: true });
  caption = h("div", { class: "preview-caption" });
  chips = h("div", { class: "chips" });
  liveRow = h("div", { class: "row live-row" });
  const playBtn = h("button", { class: "btn ghost icon", type: "button", title: t("preview.pause"),
    onClick: (e) => {
      playing = !playing;
      e.currentTarget.replaceChildren(icon(playing ? "pause" : "play"));
      e.currentTarget.title = playing ? t("preview.pause") : t("preview.play");
    } }, icon("pause"));
  root = h("div", { class: "preview-inner" },
    h("div", { class: "preview-head" }, icon("tv"), h("span", {}, t("preview.title")), h("span", { class: "spacer" }),
      store.focus.type === "playlist" ? playBtn : null),
    h("div", { class: "stage" }, canvas, img),
    caption,
    store.focus.type === "playlist" ? chips : null,
    h("div", { class: "panel" }, liveRow));
  container.replaceChildren(root);
  lastSource = "";
  renderChips();
  renderLive();
}

export async function startPreview(container) {
  await loadFont();
  mountPreview(container);
  setInterval(tick, 100);
  subscribe((what) => {
    if (what === "status") renderLive();
    if (what === "focus" || what === "render") mountPreview(container);
    if (what === "draft") renderChips();
  });
}

