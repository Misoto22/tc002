// Overview: what the clock shows now (as pictures), the focus timer, and whether the
// clock, the service and tc002.toml agree. Session counts and plan limits live on the
// clock itself, not here.

import { hooksConnected } from "../agents.js";
import { appName, t } from "../i18n.js";
import { applySaved, load, setFocus, store } from "../store.js";
import { post } from "../api.js";
import { badge, button, h, icon, pageHead, panel, row, section, toast } from "../ui.js";
import { clockProblem, page, serviceSummary, slotKey, thumb } from "./common.js";

function nowShowing() {
  const r = store.draft.rotation;
  const single = r.mode === "single" && r.show;
  const items = single ? [r.show] : r.slots;
  const total = r.slots.reduce((sum, s) => sum + Number(s.seconds), 0);
  let text = t("mode.nowEmpty");
  if (single) text = t("mode.nowSingle", { name: appName(slotKey(r.show)) });
  else if (items.length) text = t("mode.nowCycle", { n: items.length, s: total });
  return [
    section(t("overview.now"), h("span", { class: "spacer" }),
      h("a", { class: "link", href: "#rotation" }, `${t("overview.edit")} →`)),
    h("a", { class: "now-card", href: "#rotation" },
      h("div", { class: "now-strip" }, ...items.slice(0, 6).map((s) => h("figure", {},
        thumb(slotKey(s), Boolean(s.screen)),
        h("figcaption", {}, appName(slotKey(s)), single ? null : h("span", { class: "muted" }, ` ${s.seconds}s`))))),
      h("div", { class: "now-text" }, icon(single ? "pin" : "repeat"), text)),
  ];
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
  return [section(t("focus.title")), panel(h("div", { class: "row library-row" },
    thumb("focus", true),
    h("div", { class: "row-text" },
      h("div", { class: "row-title" }, appName("focus")),
      h("div", { class: "row-hint" }, running ? t(`focus.${running.phase}`, { min: Math.ceil(running.left / 60) }) : t("focus.idle"))),
    h("div", { class: "row-control" }, running ? button(t("focus.stop"), () => act("stop"), { ico: "x" })
      : button(t("focus.start"), () => act("start"), { kind: "primary", ico: "play" }))))];
}

function statusPanel() {
  const { clock, integrations } = store.state;
  const drift = clock.drift ?? [];
  const running = integrations.service.startsWith("state: running");
  return panel(
    row(t("row.clock"), clock.online ? `${clock.host} · ${t("fact.firmware")} ${clock.base.appVer}` : clockProblem(clock),
      [badge(clock.online ? t("badge.online") : t("badge.offline"), clock.online ? "ok" : "bad"),
        h("a", { class: "btn ghost", href: "#setup", title: t("overview.wizardHint") }, icon("wand-sparkles"), t("overview.wizard"))],
      { icon: "wifi" }),
    row(t("row.service"), serviceSummary(integrations.service),
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

export function overview() {
  setFocus({ type: "rotation" });
  return page(
    pageHead(t("page.overview"), t("desc.overview"), button(t("btn.refresh"), load, { ico: "refresh-cw" })),
    ...nowShowing(),
    ...(focusBlock() ?? []),
    section(t("section.status")), statusPanel(),
  );
}
