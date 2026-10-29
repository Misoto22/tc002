// First run: find the clock, pick a preset, connect agents, start the service.

import { integration } from "../agents.js";
import { get, post } from "../api.js";
import { appName, t } from "../i18n.js";
import { load, setFocus, store } from "../store.js";
import { appIcon, button, h, icon, pageHead, toast } from "../ui.js";
import { page } from "./common.js";

const draft = { host: "", preset: "developer", agents: true, service: true, scan: null, busy: false };

async function scan(rerender) {
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

async function finish(rerender) {
  draft.busy = true;
  rerender();
  try {
    await post("/api/setup", { host: draft.host.trim(), preset: draft.preset });
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

const step = (n, title, ...body) => h("section", { class: "step" },
  h("div", { class: "step-head" }, h("span", { class: "step-num" }, n), h("h2", {}, title)), ...body);

function findStep(rerender) {
  const s = draft.scan;
  const found = (s?.clocks ?? []).map((c) => h("button", {
    type: "button", class: "choice", "aria-pressed": String(draft.host === c.host),
    onClick: () => { draft.host = c.host; rerender(); },
  }, icon("tv"), h("span", { class: "choice-title" }, c.name), h("span", { class: "mono muted" }, `${c.host} · ${c.appVer ?? ""}`)));
  let status = t("setup.scanning");
  if (s && !s.pending) status = s.clocks.length ? t("setup.found", { subnet: s.subnet }) : t("setup.none", { subnet: s.subnet ?? "—" });
  return step(1, t("setup.find"),
    h("p", { class: "muted" }, status, " ", s && !s.pending ? button(t("setup.scan"), () => scan(rerender), { kind: "ghost", ico: "refresh-cw" }) : null),
    found.length ? h("div", { class: "choices" }, ...found) : null,
    h("label", { class: "field-label" }, t("setup.address"),
      h("input", { class: "field mono", value: draft.host, placeholder: "192.168.1.50", autocomplete: "off",
        onInput: (e) => { draft.host = e.target.value; } })));
}

function presetStep(rerender) {
  return step(2, t("setup.pick"), h("div", { class: "choices" }, ...store.state.presets.map((p) => h("button", {
    type: "button", class: "choice", "aria-pressed": String(draft.preset === p.id),
    onClick: () => { draft.preset = p.id; rerender(); },
  }, h("span", { class: "choice-icons" }, ...p.slots.map((s) => appIcon(s.screen ?? s.builtin, "sm"))),
  h("span", { class: "choice-title" }, t(`preset.${p.id}.name`)),
  h("span", { class: "muted" }, p.slots.map((s) => appName(s.screen ?? s.builtin)).join(" · "))))));
}

const check = (label, hint, key) => h("label", { class: "check" },
  h("input", { type: "checkbox", checked: draft[key], onChange: (e) => { draft[key] = e.target.checked; } }),
  h("span", {}, h("span", { class: "check-title" }, label), hint && h("span", { class: "muted" }, hint)));

export function setup() {
  setFocus({ type: "rotation" });
  const rerender = () => document.getElementById("page").replaceChildren(setup());
  if (draft.scan === null) setTimeout(() => scan(rerender));
  return page(
    pageHead(t("setup.title"), t("setup.desc")),
    findStep(rerender),
    presetStep(rerender),
    step(3, t("setup.agents"), check(t("int.hooks"), t("setup.agentsHint"), "agents")),
    step(4, t("int.mac"), check(t("setup.service"), t("int.serviceHint"), "service")),
    h("div", { class: "step-actions" },
      button(draft.busy ? t("setup.working") : t("setup.finish"), () => finish(rerender),
        { kind: "accent", ico: draft.busy ? "loader-circle" : "check", disabled: draft.busy || !draft.host.trim() })),
  );
}
