// First run, from a clock still in its box to a working setup: find it (or put a new one
// on Wi-Fi through its hotspot), check its firmware, set time zone and city, pick a
// layout, connect agents, start the service. The Wi-Fi password is sent to the clock
// and kept nowhere, not even in this draft.

import { integration } from "../agents.js";
import { get, post } from "../api.js";
import { cityPicker } from "../citypicker.js";
import { appName, t } from "../i18n.js";
import { load, setFocus, store } from "../store.js";
import { TIMING } from "../timing.js";
import { appIcon, badge, button, h, icon, pageHead, select, toast } from "../ui.js";
import { page } from "./common.js";

const draft = {
  host: "", preset: "developer", agents: true, service: true, scan: null, busy: false,
  timezone: null, weather: null, fresh: null, // fresh: the new-clock (hotspot) flow, when open
};

const timezoneGuess = () => {
  const hours = Math.round(-new Date().getTimezoneOffset() / 60);
  return hours ? `UTC${hours > 0 ? "+" : ""}${hours}` : "UTC+0";
};

const onSetup = () => location.hash.slice(1) === "setup";
let rerender = () => {};

async function scan() {
  draft.scan = { pending: true };
  rerender();
  try {
    const found = await get("/api/discover");
    draft.scan = found;
    if (!draft.host && found.clocks.length) draft.host = found.clocks[0].host;
  } catch (err) {
    draft.scan = { subnet: null, clocks: [], error: err.message };
  }
  rerender();
}

// ---- a brand-new clock: hotspot -> Wi-Fi details -> back on the home network ---------

function startFresh() {
  draft.fresh = { stage: "hotspot", onHotspot: false, ssid: "", hotspot: null };
  pollHotspot();
  rerender();
}

async function pollHotspot() {
  if (!draft.fresh || draft.fresh.stage !== "hotspot" || !onSetup()) return;
  try {
    const status = await get("/api/wifi/status");
    const changed = status.onHotspot !== draft.fresh.onHotspot || !draft.fresh.hotspot;
    Object.assign(draft.fresh, { onHotspot: status.onHotspot, hotspot: status });
    if (changed) rerender(); // only on change: a redraw would clear what is being typed
  } catch (err) {
    console.warn("tc002: hotspot check failed", err); // the next check retries
  }
  setTimeout(pollHotspot, TIMING.hotspotPollMs);
}

async function joinHotspot() {
  try {
    await post("/api/wifi/join-hotspot", {});
  } catch (err) {
    toast(err.title, err.message, "error");
  }
}

async function sendWifi(password) {
  const f = draft.fresh;
  try {
    await post("/api/wifi/send", { ssid: f.ssid, password });
  } catch (err) {
    toast(err.title, err.message, "error");
    return;
  }
  f.stage = "joining";
  rerender();
  const back = await post("/api/wifi/rejoin", { ssid: f.ssid }).catch((err) => ({ detail: err.message }));
  f.rejoinProblem = back.rejoined ? null : back.detail;
  waitForClock(Date.now());
}

async function waitForClock(started) {
  if (!draft.fresh || !onSetup()) return;
  await scan();
  if (draft.scan?.clocks?.length) {
    draft.fresh = null; // found: continue as with any clock
    rerender();
    return;
  }
  if (Date.now() - started > TIMING.clockJoinMs) {
    draft.fresh.stage = "notFound";
    rerender();
    return;
  }
  setTimeout(() => waitForClock(started), TIMING.discoverRetryMs);
}

function freshSteps() {
  const f = draft.fresh;
  const close = button(t("setup.freshCancel"), () => { draft.fresh = null; rerender(); }, { kind: "ghost" });
  if (f.stage === "hotspot") {
    const hs = f.hotspot ?? {};
    return h("div", { class: "fresh" },
      h("p", {}, t("setup.freshPlug", { ssid: hs.hotspot ?? "U-Clock" })),
      h("div", { class: "fresh-row" },
        button(t("setup.freshJoin", { ssid: hs.hotspot ?? "U-Clock" }), joinHotspot, { kind: "primary", ico: "wifi" }),
        h("span", { class: "muted" }, t("setup.freshManual", { password: hs.hotspotPassword ?? "" }))),
      h("p", { class: f.onHotspot ? "ok-line" : "muted" }, icon(f.onHotspot ? "circle-check" : "loader-circle", f.onHotspot ? "icon" : "icon spin"),
        f.onHotspot ? t("setup.freshSeen") : t("setup.freshWaiting")),
      f.onHotspot ? wifiForm() : null,
      close);
  }
  if (f.stage === "joining") {
    return h("div", { class: "fresh" },
      h("p", { class: "muted" }, icon("loader-circle", "icon spin"), t("setup.freshJoining", { ssid: f.ssid })),
      f.rejoinProblem ? h("p", { class: "warn-line" }, t("setup.freshRejoin", { ssid: f.ssid })) : null, close);
  }
  return h("div", { class: "fresh" },
    h("p", { class: "warn-line" }, t("setup.freshNotFound", { ssid: f.ssid })),
    h("div", { class: "fresh-row" }, button(t("setup.freshRetry"), startFresh, { ico: "rotate-ccw" }), close));
}

function wifiForm() {
  const f = draft.fresh;
  const ssid = h("input", { class: "field", value: f.ssid, autocomplete: "off", "aria-label": t("setup.ssid"),
    placeholder: t("setup.ssid"), onInput: (e) => { f.ssid = e.target.value; } });
  const password = h("input", { class: "field", type: "password", autocomplete: "off", "aria-label": t("setup.wifiPassword"),
    placeholder: t("setup.wifiPassword") });
  return h("div", { class: "fresh-form" },
    h("label", { class: "field-label" }, t("setup.ssid"), ssid),
    h("label", { class: "field-label" }, t("setup.wifiPassword"), password),
    h("p", { class: "muted" }, t("setup.wifiHint")),
    button(t("setup.freshSend"), () => sendWifi(password.value), { kind: "primary", ico: "send" }));
}

// ---- steps --------------------------------------------------------------------------

const step = (n, title, ...body) => h("section", { class: "step" },
  h("div", { class: "step-head" }, h("span", { class: "step-num" }, n), h("h2", {}, title)), ...body);

function clockChoice(c) {
  return h("button", {
    type: "button", class: "choice", "aria-pressed": String(draft.host === c.host),
    onClick: () => { draft.host = c.host; rerender(); },
  }, icon("tv"), h("span", { class: "choice-title" }, c.name),
  h("span", { class: "mono muted" }, `${c.host} · ${c.appVer ?? ""}`),
  c.supported === false ? badge(t("setup.oldFirmware", { min: store.state.minFirmware }), "warn") : null);
}

function findStep() {
  const s = draft.scan;
  let status = t("setup.scanning");
  if (s && !s.pending) status = s.clocks.length ? t("setup.found", { subnet: s.subnet ?? "" }) : t("setup.none", { subnet: s.subnet ?? "—" });
  return step(1, t("setup.find"),
    draft.fresh ? freshSteps() : [
      h("p", { class: "muted" }, status, " ",
        s && !s.pending ? button(t("setup.scan"), scan, { kind: "ghost", ico: "refresh-cw" }) : null),
      s?.clocks?.length ? h("div", { class: "choices" }, ...s.clocks.map(clockChoice)) : null,
      h("label", { class: "field-label" }, t("setup.address"),
        h("input", { class: "field mono", value: draft.host, placeholder: t("setup.addressPlaceholder"), autocomplete: "off",
          onInput: (e) => { draft.host = e.target.value; } })),
      h("p", { class: "muted" }, t("setup.freshAsk"), " ",
        button(t("setup.freshStart"), startFresh, { kind: "ghost", ico: "wifi" })),
    ]);
}

function placeStep() {
  draft.timezone ??= timezoneGuess();
  return step(2, t("setup.place"),
    h("div", { class: "place" },
      h("label", { class: "field-label" }, t("field.timezone"),
        select(store.state.timezones.map((z) => [z, z]), draft.timezone, (z) => { draft.timezone = z; }, t("field.timezone"))),
      h("div", { class: "field-label" }, t("field.city"),
        cityPicker(draft.weather ?? {}, (picked) => { draft.weather = picked; }))));
}

function presetStep() {
  return step(3, t("setup.pick"), h("div", { class: "choices" }, ...store.state.presets.map((p) => h("button", {
    type: "button", class: "choice", "aria-pressed": String(draft.preset === p.id),
    onClick: () => { draft.preset = p.id; rerender(); },
  }, h("span", { class: "choice-icons" }, ...p.slots.map((s) => appIcon(s.screen ?? s.builtin, "sm"))),
  h("span", { class: "choice-title" }, t(`preset.${p.id}.name`)),
  h("span", { class: "muted" }, p.slots.map((s) => appName(s.screen ?? s.builtin)).join(" · "))))));
}

const check = (label, hint, key) => h("label", { class: "check" },
  h("input", { type: "checkbox", checked: draft[key], onChange: (e) => { draft[key] = e.target.checked; } }),
  h("span", {}, h("span", { class: "check-title" }, label), hint && h("span", { class: "muted" }, hint)));

async function finish() {
  draft.busy = true;
  rerender();
  try {
    await post("/api/setup", { host: draft.host.trim(), preset: draft.preset, timezone: draft.timezone, weather: draft.weather });
    if (draft.agents) await integration("connect-claude");
    if (draft.service) await integration("install-service");
    await load();
    toast(t("setup.done"));
    location.hash = "overview";
  } catch (err) {
    toast(err.title, err.message, "error");
  } finally {
    draft.busy = false;
    rerender();
  }
}

export function setup() {
  setFocus({ type: "rotation" });
  rerender = () => { if (onSetup()) document.getElementById("page").replaceChildren(setup()); };
  if (draft.scan === null) setTimeout(scan);
  const ready = draft.host.trim() && !draft.fresh;
  return page(
    pageHead(t("setup.title"), t("setup.desc")),
    findStep(),
    placeStep(),
    presetStep(),
    step(4, t("setup.agents"), check(t("int.hooks"), t("setup.agentsHint"), "agents")),
    step(5, t("int.mac"), check(t("setup.service"), t("int.serviceHint"), "service")),
    h("div", { class: "step-actions" },
      button(draft.busy ? t("setup.working") : t("setup.finish"), finish,
        { kind: "accent", ico: draft.busy ? "loader-circle" : "check", disabled: draft.busy || !ready })),
  );
}
