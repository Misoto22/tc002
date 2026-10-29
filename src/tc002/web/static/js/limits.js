// Plan limit cards: one per agent, with its 5-hour and 7-day allowance as meters.

import { integration } from "./agents.js";
import { t, until } from "./i18n.js";
import { store } from "./store.js";
import { appIcon, button, countUp, h } from "./ui.js";

const AGENTS = { claude: "Claude Code", codex: "Codex" };
const WARN = 80;

function shortTokens(n) {
  for (const [size, suffix] of [[1e9, "B"], [1e6, "M"], [1e3, "K"]]) {
    if (n >= size) return `${(n / size).toFixed(n / size < 10 ? 1 : 0)}${suffix}`;
  }
  return String(n);
}

function resetText(unix) {
  const left = until(unix);
  if (!left) return "";
  if (unix - Date.now() / 1000 < 86400) return t("limits.resetsIn", { t: left });
  const when = new Date(unix * 1000).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" });
  return t("limits.resetsAt", { t: when });
}

function meter(label, pct, reset, agent, key) {
  const known = pct !== null && pct !== undefined;
  const value = known ? Math.round(pct) : null;
  return h("div", { class: `meter${known && value >= WARN ? " warn" : ""}` },
    h("div", { class: "meter-label" }, label),
    h("div", { class: "meter-num" }, known ? countUp(h("span", { class: "num" }), value, key) : "—",
      known ? h("span", {}, "%") : null),
    h("div", { class: "meter-track", role: "img", "aria-label": `${label}: ${known ? `${value}%` : t("limits.unknown")}` },
      h("span", { class: `meter-fill agent-${agent}`, style: `width:${known ? Math.min(100, value) : 0}%` })),
    h("div", { class: "meter-hint" }, known ? resetText(reset) : t("limits.unknown")));
}

export function limitCard(agent) {
  const u = store.state.agents.usage[agent];
  const known = u.limit_5h !== null || u.limit_week !== null;
  const connected = agent !== "claude" || store.state.integrations.statusline;
  let note = null;
  if (!known && agent === "claude" && !connected) {
    note = h("div", { class: "limit-note" }, h("p", {}, t("limits.claudeConnect")),
      button(t("int.connect"), () => integration("connect-claude"), { kind: "primary", ico: "plug" }));
  } else if (!known) {
    note = h("p", { class: "limit-note muted" }, t(agent === "claude" ? "limits.claudeHint" : "limits.codexHint"));
  }
  return h("div", { class: `limit-card${known ? "" : " unknown"}` },
    h("div", { class: "limit-head" }, appIcon(agent === "claude" ? "claude" : "codex"),
      h("span", { class: "limit-name" }, AGENTS[agent]),
      h("span", { class: "spacer" }),
      h("span", { class: "muted mono" }, t("limits.tokensToday", { n: shortTokens(u.today) }))),
    h("div", { class: "meters" },
      meter(t("limits.fiveHour"), u.limit_5h, u.reset_5h, agent, `${agent}.5h`),
      meter(t("limits.week"), u.limit_week, u.reset_week, agent, `${agent}.week`)),
    note);
}

export const limitCards = () => h("div", { class: "limit-cards" }, limitCard("claude"), limitCard("codex"));
