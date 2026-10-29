import { hooksConnected, orderedSessions } from "../agents.js";
import { t } from "../i18n.js";
import { limitCards } from "../limits.js";
import { quickControls } from "../quick.js";
import { applySaved, load, setFocus, store } from "../store.js";
import { post } from "../api.js";
import { badge, button, h, pageHead, panel, row, section, toast } from "../ui.js";
import { page } from "./common.js";
import { sessionRow, stateFigures } from "./sessions.js";

function sessionsBlock() {
  const { counts } = store.state.agents;
  const first = orderedSessions().filter((s) => s.state === "waiting" || s.state === "working").slice(0, 3);
  return h("div", { class: "block" },
    section(t("page.sessions"), h("span", { class: "spacer" }),
      h("a", { class: "link", href: "#sessions" }, `${t("sessions.all")} →`)),
    stateFigures(counts),
    first.length ? h("div", { class: "session-list compact" }, ...first.map(sessionRow)) : null);
}

function statusPanel() {
  const { clock, integrations } = store.state;
  const drift = clock.drift ?? [];
  const running = integrations.service.startsWith("state: running");
  return panel(
    row(t("row.clock"), clock.online ? `${clock.host} · ${t("fact.firmware")} ${clock.base.appVer}` : { text: clock.error, warn: true },
      badge(clock.online ? t("badge.online") : t("badge.offline"), clock.online ? "ok" : "bad"), { icon: "wifi" }),
    row(t("row.service"), integrations.service.split("\n")[0],
      badge(running ? t("badge.running") : t("badge.stopped"), running ? "ok" : "warn"), { icon: "power" }),
    row(t("int.hooks"), t("int.hooksHint"),
      h("a", { class: "link", href: "#integrations" },
        badge(hooksConnected() ? t("badge.installed") : t("badge.missing"), hooksConnected() ? "ok" : "warn")),
      { app: "claude" }),
    row(t("row.sync"), drift.length ? { text: t("row.differs", { list: drift.join(", ") }), warn: true } : t("row.everythingSynced"),
      drift.length ? button(t("btn.applyNow"), applySaved, { kind: "primary", ico: "refresh-cw" }) : badge(t("badge.inSync"), "ok"),
      { icon: "refresh-cw" }),
  );
}

// The focus timer: start and stop it here; the focus screen on the clock shows it.
function focusBlock() {
  if (!store.draft.screens.enabled.includes("focus")) return null;
  const running = store.state.focus;
  const act = async (action) => {
    try {
      await post("/api/focus", { action });
      await load();
    } catch (err) {
      toast(err.title, err.message, "error");
    }
  };
  return panel(row(t("focus.title"),
    running ? t(`focus.${running.phase}`, { min: Math.ceil(running.left / 60) }) : t("focus.idle"),
    running ? button(t("focus.stop"), () => act("stop"), { ico: "x" })
      : button(t("focus.start"), () => act("start"), { kind: "primary", ico: "play" }),
    { app: "focus" }));
}

export function overview() {
  setFocus({ type: "rotation" });
  const { clock } = store.state;
  return page(
    pageHead(t("page.overview"), t("desc.overview"), button(t("btn.refresh"), load, { ico: "refresh-cw" })),
    sessionsBlock(),
    h("div", { class: "block" },
      section(t("limits.title"), h("span", { class: "spacer" }),
        h("a", { class: "link", href: "#rotation" }, `${t("limits.onClock")} →`)),
      limitCards()),
    focusBlock(),
    clock.online && section(t("quick.title"), h("span", { class: "spacer" }),
      h("a", { class: "link", href: "#display" }, `${t("quick.more")} →`)),
    clock.online && h("div", { class: "panel quick-grid" }, ...quickControls()),
    section(t("section.status")), statusPanel(),
  );
}
