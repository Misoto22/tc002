import { hooksConnected, integration } from "../agents.js";
import { get, post } from "../api.js";
import { t } from "../i18n.js";
import { factList, status } from "../livecheck.js";
import { setFocus, store } from "../store.js";
import { badge, button, h, icon, pageHead, panel, row, section, toast } from "../ui.js";
import { clockProblem, page, serviceSummary } from "./common.js";

let logText = null; // shown under the service row once asked for
let clockResult; // undefined: not asked; null: asking; else the clock's answer

// Ask the clock now and show the answer under its row: reachable or not, how fast, and
// its firmware and Wi-Fi.
async function checkClock(rerender) {
  clockResult = null;
  rerender();
  clockResult = await get("/api/clock/check").catch((err) => ({ ok: false, error: err.message, ms: 0 }));
  rerender();
}

async function toggleLog(rerender) {
  if (logText !== null) { logText = null; rerender(); return; }
  try {
    logText = (await get("/api/log")).text || t("int.logEmpty");
  } catch (err) {
    toast(err.title, err.message, "error");
  }
  rerender();
}

function reveal(what) {
  post("/api/reveal", { what }).catch((err) => toast(err.title, err.message, "error"));
}

function hookChips(hooks) {
  return h("div", { class: "chips" }, ...Object.entries(hooks).map(([event, on]) =>
    h("span", { class: `chip mono${on === true ? "" : " missing"}` }, event)));
}

export function integrations() {
  setFocus({ type: "rotation" });
  const { integrations: it, config, clock, agents } = store.state;
  const running = it.service.startsWith("state: running");
  const installed = !it.service.startsWith("not installed");
  const rerender = () => document.getElementById("page").replaceChildren(integrations());
  const codexSeen = agents.usage.codex.source !== "none";
  return page(
    pageHead(t("page.integrations"), t("desc.integrations")),
    section(t("int.clock")),
    panel(row(clock.host ? t("int.clockAt", { host: clock.host }) : t("int.notSet"),
      clock.online ? `${t("fact.firmware")} ${clock.base.appVer}` : clockProblem(clock),
      [badge(clock.online ? t("badge.online") : t("badge.offline"), clock.online ? "ok" : "bad"),
        button(t("conn.try"), () => checkClock(rerender), { ico: "play" }),
        h("a", { class: "btn", href: "#setup" }, icon("wand-sparkles"), t("overview.wizard"))], { icon: "tv" }),
      clockResult === undefined ? null
        : h("div", { class: "check-result" }, status(clockResult), factList(clockResult) ?? "")),
    section(t("int.agents")),
    panel(
      row(t("int.hooks"), h("div", {}, t("int.hooksHint"), hookChips(it.hooks)),
        hooksConnected()
          ? button(t("int.disconnect"), () => integration("disconnect-claude"), { ico: "power" })
          : button(t("int.connect"), () => integration("connect-claude"), { kind: "primary", ico: "plug" }),
        { app: "claude" }),
      row(t("int.statusline"), t("int.statuslineHint"),
        it.statusline ? badge(t("badge.installed"), "ok")
          : button(t("int.connect"), () => integration("connect-claude"), { kind: "primary", ico: "plug" }),
        { app: "claude" }),
      row(t("int.codex"), t("int.codexHint"), badge(codexSeen ? t("int.ready") : t("limits.unknown"), codexSeen ? "ok" : ""),
        { app: "codex" })),
    section(t("int.mac")),
    panel(
      row(t("row.service"), h("div", {}, h("div", { title: serviceSummary(it.service).title }, serviceSummary(it.service).text),
        h("div", { class: "muted" }, t("int.serviceHint"))),
        [badge(running ? t("badge.running") : t("badge.stopped"), running ? "ok" : "warn"),
          installed ? button(t("int.restart"), () => integration("restart-service"), { ico: "rotate-ccw" })
            : button(t("int.install"), () => integration("install-service"), { kind: "primary", ico: "power" }),
          button(logText === null ? t("int.showLog") : t("int.hideLog"), () => toggleLog(rerender), { ico: "scroll-text" })],
        { icon: "power" }),
      logText !== null ? h("pre", { class: "log" }, logText) : null,
      row(t("int.toml"), h("span", { class: "mono" }, config.shown ?? t("int.notSet")),
        config.path ? button(t("int.reveal"), () => reveal("config"), { ico: "folder-search" }) : [],
        { icon: "sliders-horizontal" })),
  );
}
