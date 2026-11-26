import { hooksConnected, integration } from "../agents.js";
import { get, post } from "../api.js";
import { lang, t, until } from "../i18n.js";
import { factList, status } from "../livecheck.js";
import { setFocus, store } from "../store.js";
import { button, h, icon, pageHead, panel, row, section, toast } from "../ui.js";
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

// A status in a row's hint: a coloured dot and its words. Rows keep only actions on the
// right, so every control there is a button of one height.
function stateLine(tone, ...words) {
  return h("span", { class: "state-line" }, h("span", { class: `dot ${tone}` }), words.filter(Boolean).join(" · "));
}

// When an allowance refills: "in 2 h 14 min" within a day, else the weekday and time.
function resetText(unix) {
  if (!unix || unix * 1000 <= Date.now()) return null;
  if (unix * 1000 - Date.now() < 86_400_000) return t("limits.resetsIn", { t: until(unix) });
  const when = new Date(unix * 1000).toLocaleString(lang() === "zh" ? "zh-CN" : "en",
    { weekday: "short", hour: "2-digit", minute: "2-digit" });
  return t("limits.resetsAt", { t: when });
}

// One allowance as a small meter: its name and % used over a bar in the agent's colour,
// amber from the warning level and red from the critical one, as on the clock.
function meter(agent, label, pct, resets) {
  const known = typeof pct === "number";
  const { warn = 80, critical = 95 } = store.state.limits ?? {};
  const tone = !known ? "unknown" : pct >= critical ? "bad" : pct >= warn ? "warn" : agent;
  return h("div", { class: `meter ${tone}`, title: resetText(resets) ?? "" },
    h("div", { class: "meter-head" }, h("span", {}, label), h("span", { class: "meter-value" }, known ? `${Math.round(pct)}%` : "—")),
    h("div", { class: "meter-track" }, h("div", { class: "meter-fill", style: `width: ${known ? Math.min(100, Math.max(0, pct)) : 0}%` })));
}

// An agent's row: its 5-hour and 7-day allowance as meters; the hint says when they
// refill, or where the numbers come from while there are none.
function agentRow(agent, usage, sourceHint) {
  const u = usage ?? {};
  const resets = [
    typeof u.limit_5h === "number" && resetText(u.reset_5h) && `${t("limits.5h")} ${resetText(u.reset_5h)}`,
    typeof u.limit_week === "number" && resetText(u.reset_week) && `${t("limits.7d")} ${resetText(u.reset_week)}`,
  ].filter(Boolean);
  const known = typeof u.limit_5h === "number" || typeof u.limit_week === "number";
  return row(t(`agent.${agent}`), known && resets.length ? resets.join(" · ") : sourceHint,
    h("div", { class: "meters" },
      meter(agent, t("limits.5h"), u.limit_5h, u.reset_5h),
      meter(agent, t("limits.7d"), u.limit_week, u.reset_week)),
    { app: agent });
}

export function integrations() {
  setFocus({ type: "rotation" });
  const { integrations: it, config, clock, agents } = store.state;
  const running = it.service.startsWith("state: running");
  const installed = !it.service.startsWith("not installed");
  const rerender = () => document.getElementById("page").replaceChildren(integrations());
  const claudeOn = hooksConnected() && it.statusline;
  return page(
    pageHead(t("page.integrations"), t("desc.integrations")),
    section(t("int.clock")),
    panel(row(clock.host ? t("int.clockAt", { host: clock.host }) : t("int.notSet"),
      clock.online ? stateLine("ok", t("badge.online"), `${t("fact.firmware")} ${clock.base.appVer}`) : clockProblem(clock),
      [button(t("conn.try"), () => checkClock(rerender), { ico: "play" }),
        h("a", { class: "btn", href: "#setup" }, icon("wand-sparkles"), t("overview.wizard"))], { icon: "tv" }),
      clockResult === undefined ? null
        : h("div", { class: "check-result" }, status(clockResult), factList(clockResult) ?? "")),
    section(t("int.agents")),
    panel(
      agentRow("claude", agents.usage.claude, t("limits.claudeHint")),
      agentRow("codex", agents.usage.codex, t("int.codexHint")),
      agentRow("gemini", agents.usage.gemini, t("int.geminiHint")),
      row(t("int.claudeLink"), h("div", {}, t(claudeOn ? "int.claudeLinkOn" : "int.claudeLinkOff"), hookChips(it.hooks)),
        claudeOn
          ? button(t("int.disconnect"), () => integration("disconnect-claude"), { ico: "power" })
          : button(t("int.connect"), () => integration("connect-claude"), { kind: "primary", ico: "plug" }),
        { icon: "plug" })),
    section(t("int.mac")),
    panel(
      row(t("row.service"), h("div", {},
        h("div", { title: serviceSummary(it.service).title }, stateLine(running ? "ok" : "warn", serviceSummary(it.service).text)),
        h("div", { class: "muted" }, t("int.serviceHint"))),
        [installed ? button(t("int.restart"), () => integration("restart-service"), { ico: "rotate-ccw" })
            : button(t("int.install"), () => integration("install-service"), { kind: "primary", ico: "power" }),
          button(logText === null ? t("int.showLog") : t("int.hideLog"), () => toggleLog(rerender), { ico: "scroll-text" })],
        { icon: "power" }),
      logText !== null ? h("pre", { class: "log" }, logText) : null,
      row(t("int.toml"), h("span", { class: "mono" }, config.shown ?? t("int.notSet")),
        config.path ? button(t("int.reveal"), () => reveal("config"), { ico: "folder-search" }) : [],
        { icon: "sliders-horizontal" })),
  );
}
