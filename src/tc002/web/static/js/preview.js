// The device bar pinned above every page: what the clock would show with the current draft,
// and the switch that plays the draft on the real hardware before saving.

import { appName, t } from "./i18n.js";
import { draw } from "./led.js";
import { screenPreview } from "./media.js";
import { simulate } from "./sims.js";
import { setLive, store, subscribe } from "./store.js";
import { appIcon, h, icon, ms, toggle, token } from "./ui.js";

let els = null;
let playing = true;
let cycle = { index: 0, started: performance.now(), elapsed: 0 };
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

// What to draw now: { kind: "sim" | "gif", key, src, label }.
function source() {
  const f = store.focus;
  if (f.type === "message") return { kind: "gif", src: f.src, key: null, label: t("preview.message") };
  if (f.type === "screen") return { kind: "gif", src: screenPreview(f.key), key: f.key, label: appName(f.key) };
  if (f.type === "builtin") return { kind: "sim", key: f.key, label: appName(f.key) };
  const slots = store.draft.rotation.slots;
  if (!slots.length) return { kind: "sim", key: "clock", label: appName("clock") };
  const slot = slots[cycle.index % slots.length];
  return slot.screen
    ? { kind: "gif", src: screenPreview(slot.screen), key: slot.screen, label: appName(slot.screen) }
    : { kind: "sim", key: slot.builtin, label: appName(slot.builtin) };
}

function tick() {
  if (!store.draft || !els?.root.isConnected) return;
  const slots = store.draft.rotation.slots;
  const now = performance.now();
  if (store.focus.type === "rotation" && slots.length) {
    const slot = slots[cycle.index % slots.length];
    if (playing) cycle.elapsed = now - cycle.started;
    else cycle.started = now - cycle.elapsed;
    if (cycle.elapsed >= slot.seconds * 1000) cycle = { index: (cycle.index + 1) % slots.length, started: now, elapsed: 0 };
    paintChips(cycle.elapsed / (slot.seconds * 1000));
  }
  const src = source();
  const { settings, apps } = merged();
  els.stage.style.filter = `brightness(${brightness(settings).toFixed(2)})`;
  const key = JSON.stringify(src);
  if (key !== lastSource) { // cross-fade between sources
    lastSource = key;
    els.stage.animate([{ opacity: 0 }, { opacity: 1 }], { duration: ms("--led-fade"), easing: token("--ease") });
    els.title.replaceChildren(...[ // native replaceChildren would print a null as "null"
      src.key ? appIcon(src.key, "sm") : icon("message-square-text"),
      h("span", {}, src.label),
      src.kind === "sim" ? h("span", { class: "muted" }, `${t("preview.approx")}${src.key === "weather" ? ` · ${t("preview.sample")}` : ""}`) : null,
    ].filter(Boolean));
  }
  if (src.kind === "gif") {
    els.canvas.hidden = true;
    els.img.hidden = false;
    if (els.img.getAttribute("src") !== src.src) els.img.src = src.src;
  } else {
    els.img.hidden = true;
    els.canvas.hidden = false;
    draw(els.canvas, simulate(src.key, settings, apps, Date.now()));
  }
}

function renderChips() {
  const slots = store.focus.type === "rotation" ? store.draft.rotation.slots : [];
  els.chips.replaceChildren(...slots.map((s, i) => h("button", {
    class: "chip", type: "button", title: `${s.seconds}s`,
    onClick: () => { cycle = { index: i, started: performance.now(), elapsed: 0 }; },
  }, appIcon(s.screen ?? s.builtin), appName(s.screen ?? s.builtin))));
}

function paintChips(progress) {
  [...els.chips.children].forEach((chip, i) => {
    const current = i === cycle.index % els.chips.children.length;
    chip.classList.toggle("current", current);
    chip.style.setProperty("--p", current ? Math.min(1, progress).toFixed(3) : 0);
  });
}

function renderControls() {
  const online = store.state?.clock.online;
  const rotation = store.focus.type === "rotation" && store.draft.rotation.slots.length > 1;
  els.controls.replaceChildren(...[
    rotation ? h("button", { class: "btn ghost icon", type: "button", title: playing ? t("preview.pause") : t("preview.play"),
      onClick: () => { playing = !playing; renderControls(); } }, icon(playing ? "pause" : "play")) : null,
    h("label", { class: "live-label", title: online ? t("preview.liveHint") : t("preview.offline") },
      toggle(store.live.on, (on) => setLive(on), { label: t("preview.live"), disabled: !online }),
      store.live.on ? h("span", { class: "live-dot" }) : null,
      store.live.on ? t("preview.liveOn") : t("preview.live")),
  ].filter(Boolean));
}

function mount(container) {
  els = {
    canvas: h("canvas", { width: 520, height: 160, class: "led-canvas", "aria-label": t("preview.title") }),
    img: h("img", { class: "led-img", alt: "", hidden: true }),
    title: h("div", { class: "device-title" }),
    chips: h("div", { class: "chips" }),
    controls: h("div", { class: "device-actions" }),
  };
  els.stage = h("div", { class: "stage" }, els.canvas, els.img);
  els.root = h("div", { class: "device-inner" }, els.stage,
    h("div", { class: "device-info" }, els.title, els.chips, els.controls));
  container.replaceChildren(els.root);
  lastSource = "";
  renderChips();
  renderControls();
}

export function startPreview(container) {
  mount(container);
  setInterval(tick, 100);
  subscribe((what) => {
    if (what === "status") renderControls();
    if (what === "focus" || what === "render") mount(container);
    if (what === "draft") renderChips();
  });
}
