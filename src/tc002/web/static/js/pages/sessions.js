import { hooksConnected, integration, orderedSessions } from "../agents.js";
import { ago, t } from "../i18n.js";
import { setFocus, show, store } from "../store.js";
import { button, countUp, h, icon, pageHead, toast } from "../ui.js";
import { page } from "./common.js";

export const STATES = ["waiting", "working", "done", "idle"];

// Four figures: how many sessions are in each state.
export function stateFigures(counts) {
  return h("div", { class: "figures" }, ...STATES.map((s) => h("div", { class: `figure state-${s}` },
    countUp(h("div", { class: "figure-num" }), counts[s] ?? 0, `sessions.${s}`),
    h("div", { class: "figure-label" }, t(`state.${s}`)),
    h("div", { class: "figure-hint" }, t(`state.${s}Hint`)))));
}

function copyResume(id) {
  const cmd = `claude --resume ${id}`;
  navigator.clipboard.writeText(cmd)
    .then(() => toast(t("sessions.copied", { cmd })))
    .catch((err) => toast(t("sessions.copy"), err.message, "error"));
}

export function sessionRow(s) {
  return h("div", { class: `session state-${s.state}` },
    h("span", { class: "state-dot", "aria-hidden": "true" }),
    h("div", { class: "session-main" },
      h("div", { class: "session-title" }, h("span", { class: "session-project" }, s.project),
        h("span", { class: "session-state" }, t(`state.${s.state}`))),
      s.message && h("div", { class: "session-message" }, s.message)),
    h("span", { class: "session-age mono" }, ago(s.secondsInState)),
    h("div", { class: "session-actions" },
      button("", () => show({ screen: "claude" }), { kind: "ghost icon", ico: "tv", title: t("btn.showNow") }),
      button("", () => copyResume(s.id), { kind: "ghost icon", ico: "copy", title: t("sessions.copy") })));
}

export function sessions() {
  setFocus({ type: "screen", key: "claude" });
  const { counts } = store.state.agents;
  const list = orderedSessions();
  return page(
    pageHead(t("page.sessions"), t("desc.sessions")),
    stateFigures(counts),
    list.length
      ? h("div", { class: "session-list" }, ...list.map(sessionRow))
      : h("div", { class: "empty" }, icon("terminal"), h("p", {}, t("sessions.empty")),
        hooksConnected() ? null
          : button(t("sessions.connect"), () => integration("connect-claude"), { kind: "primary", ico: "plug" })),
  );
}
